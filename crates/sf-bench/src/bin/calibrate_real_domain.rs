use clap::Parser;
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, LockSpec, MAX_TOPK};
use sf_proxy::{BatchEmbedderClient, TeiHttpEmbedder};
use sf_storage::{calibrate_matrix, write_locks_with_manifests, CorpusManifest, HotRegistry};

#[derive(Debug, Parser)]
#[command(
    name = "calibrate_real_domain",
    about = "Calibrate a real domain hypercube lock in LanceDB using live TEI embeddings"
)]
struct Args {
    #[arg(long, default_value = "python")]
    domain_id: String,
    #[arg(long, default_value = "http://127.0.0.1:8080")]
    tei_url: String,
    #[arg(long, default_value = "data/sf-lancedb")]
    lancedb_uri: String,
    #[arg(long, default_value = "domain_hypercubes")]
    table: String,
    #[arg(long, default_value_t = 0.50)]
    l1_threshold: f32,
    #[arg(long, default_value_t = 0.50)]
    l2_threshold: f32,
}

const PYTHON_CORPUS: &[&str] = &[
    "def fibonacci_generator(n: int):\n    a, b = 0, 1\n    while a < n:\n        yield a\n        a, b = b, a + b",
    "import asyncio\nasync def fetch_payload(endpoint: str) -> dict:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(endpoint) as response:\n            return await response.json()",
    "class BinarySearchTree:\n    def __init__(self, value: int):\n        self.val = value\n        self.left = None\n        self.right = None",
    "def quicksort(arr: list[int]) -> list[int]:\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    return quicksort([x for x in arr if x < pivot]) + [x for x in arr if x == pivot] + quicksort([x for x in arr if x > pivot])",
    "import json\nfrom typing import Any, Dict\ndef parse_config(file_path: str) -> Dict[str, Any]:\n    with open(file_path, 'r', encoding='utf-8') as fh:\n        return json.load(fh)",
    "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass TelemetryMetric:\n    name: str\n    value: float\n    timestamp: int",
    "import hashlib\ndef compute_sha256(content: bytes) -> str:\n    hasher = hashlib.sha256()\n    hasher.update(content)\n    return hasher.hexdigest()",
    "def bubble_sort(items: list) -> list:\n    n = len(items)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if items[j] > items[j + 1]:\n                items[j], items[j + 1] = items[j + 1], items[j]\n    return items",
    "import re\ndef extract_emails(text: str) -> list[str]:\n    pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+'\n    return re.findall(pattern, text)",
    "import math\ndef euclidean_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:\n    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)",
    "def memoize(fn):\n    cache = {}\n    def wrapper(*args):\n        if args not in cache:\n            cache[args] = fn(*args)\n        return cache[args]\n    return wrapper",
    "import os\ndef walk_directory(root_dir: str) -> list[str]:\n    collected = []\n    for root, _, files in os.walk(root_dir):\n        for file in files:\n            collected.append(os.path.join(root, file))\n    return collected",
    "from collections import defaultdict, deque\ndef bfs_shortest_path(graph: dict, start: str, target: str):\n    queue = deque([[start]])\n    visited = {start}\n    while queue:\n        path = queue.popleft()\n        node = path[-1]\n        if node == target:\n            return path\n        for neighbor in graph.get(node, []):\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append(path + [neighbor])\n    return None",
    "def matrix_multiply(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:\n    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]",
    "import sys\ndef print_system_info():\n    print(f'Python version: {sys.version}')\n    print(f'Platform: {sys.platform}')",
    "class LRUCache:\n    def __init__(self, capacity: int):\n        self.cap = capacity\n        self.cache = {}\n    def get(self, key: int) -> int:\n        if key not in self.cache: return -1\n        val = self.cache.pop(key)\n        self.cache[key] = val\n        return val",
    "def parse_csv_lines(csv_text: str) -> list[list[str]]:\n    return [line.strip().split(',') for line in csv_text.strip().splitlines() if line.strip()]",
    "def is_prime(number: int) -> bool:\n    if number <= 1: return False\n    for factor in range(2, int(number**0.5) + 1):\n        if number % factor == 0: return False\n    return True",
    "import time\nclass Timer:\n    def __enter__(self):\n        self.start = time.perf_counter()\n        return self\n    def __exit__(self, *args):\n        self.elapsed = time.perf_counter() - self.start",
    "def count_word_frequencies(document: str) -> dict[str, int]:\n    counts = {}\n    for word in document.lower().split():\n        counts[word] = counts.get(word, 0) + 1\n    return counts",
];

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    println!("[CALIBRATE] Connecting to TEI at {}...", args.tei_url);
    let embedder = TeiHttpEmbedder::new(&args.tei_url);

    let mut vectors = Vec::with_capacity(PYTHON_CORPUS.len());
    for (i, chunk) in PYTHON_CORPUS.chunks(2).enumerate() {
        print!(
            "  Embedding batch {}/{}... ",
            i + 1,
            PYTHON_CORPUS.len().div_ceil(2)
        );
        let batch_vecs = embedder.embed_batch_f32(chunk).await?;
        println!("OK (got {})", batch_vecs.len());
        vectors.extend(batch_vecs);
    }

    let mut flat = Vec::with_capacity(vectors.len() * 1024);
    for vec in &vectors {
        flat.extend_from_slice(&vec.data);
    }

    println!("[CALIBRATE] Running calibrate_matrix on flat tensor...");
    let calib = calibrate_matrix(&flat, 0).map_err(|e| e.to_string())?;

    let mut top_k = [0u16; MAX_TOPK];
    top_k[..103].copy_from_slice(&calib.top_k);

    let centroid = AlignedVec1024::from_slice(&calib.centroid)?;
    let lo = AlignedVec1024::from_slice(&calib.lo)?;
    let hi = AlignedVec1024::from_slice(&calib.hi)?;

    let lock = DomainHypercubeLock::from_spec(LockSpec {
        domain_id: args.domain_id.clone(),
        centroid,
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: calib.noise_mask,
        top_k_indices: top_k,
        top_k_len: calib.top_k_len,
        quorum_k: 103,
        l1_cosine_threshold: args.l1_threshold,
        l2_clause_threshold: args.l2_threshold,
        polarity: 0,
        domain_version: 1,
    });

    println!(
        "[CALIBRATE] Calibrated lock '{}': active_dims={}, L1={}, L2={}",
        args.domain_id,
        lock.noise_mask.active_count(),
        lock.l1_cosine_threshold,
        lock.l2_clause_threshold
    );

    let mut all_locks = Vec::new();
    let mut manifests = Vec::new();
    if let Ok(reg) = HotRegistry::load_from_lancedb(&args.lancedb_uri, &args.table).await {
        for existing in reg.locks() {
            if existing.domain_id != args.domain_id {
                manifests.push(
                    reg.manifest(&existing.domain_id)
                        .unwrap_or(CorpusManifest::UNPROVIDED),
                );
                all_locks.push((*existing).clone());
            }
        }
        println!(
            "[CALIBRATE] Preserved {} existing locks from LanceDB",
            all_locks.len()
        );
    }

    all_locks.push(lock);
    manifests.push(calib.manifest());

    println!(
        "[CALIBRATE] Writing {} locks to LanceDB at '{}' (table '{}')...",
        all_locks.len(),
        args.lancedb_uri,
        args.table
    );
    write_locks_with_manifests(&args.lancedb_uri, &args.table, &all_locks, &manifests).await?;

    println!(
        "[CALIBRATE] Success! Domain '{}' calibrated and persisted in LanceDB.",
        args.domain_id
    );
    Ok(())
}
