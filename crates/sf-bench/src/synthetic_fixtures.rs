//! Deterministic Rompepepe stand-in. No network and no Git LFS.
//! Seed `0xDD10_0400` fixes the 55 pair locks and the 220 attack vectors.

use rand::Rng;
use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;
use sf_kernels::{
    scalar_cosine_similarity, AlignedVec1024, DomainHypercubeLock, L3InspectionMode, LockSpec,
    NoiseBitmask1024, DIM, MAX_TOPK,
};
use sf_proxy::evaluate_three_tier_cascade;

pub const FIXTURE_SEED: u64 = 0xDD10_0400;
pub const DOMAIN_NAMES: [&str; 11] = [
    "python",
    "receta",
    "legal",
    "medicina",
    "astronomia",
    "finanzas",
    "filosofia",
    "musica",
    "geologia",
    "botanica",
    "arquitectura",
];

const L1: f32 = 0.50;
const OUTSIDE: f32 = 0.03;
const INSIDE_PREFIX: usize = 80;

#[derive(Clone, Debug)]
pub struct AttackCase {
    pub lock_index: usize,
    pub vector: AlignedVec1024,
    pub cosine_should_leak: bool,
}

/// SCPB-220 (Sub-Clause Piggybacking Benchmark) stand-in.
/// Deterministic evaluation corpus with 55 Pairwise OvO Cross-Lingual Subspace Masks and 220 attack vectors.
#[derive(Clone, Debug)]
pub struct Scpb220Corpus {
    pub locks: Vec<DomainHypercubeLock>,
    pub attacks: Vec<AttackCase>,
}

/// Backwards compatibility alias for RompepepeCorpus.
pub type RompepepeCorpus = Scpb220Corpus;

/// Generate the canonical SCPB-220 (Sub-Clause Piggybacking Benchmark) corpus.
pub fn generate_scpb_220_corpus() -> Scpb220Corpus {
    let mut rng = ChaCha8Rng::seed_from_u64(FIXTURE_SEED);
    let mut locks = Vec::with_capacity(55);
    for left in 0..DOMAIN_NAMES.len() {
        for right in (left + 1)..DOMAIN_NAMES.len() {
            let spike = locks.len();
            locks.push(pair_lock(left, right, spike));
        }
    }
    debug_assert_eq!(locks.len(), 55);

    let mut attacks = Vec::with_capacity(220);
    for (lock_index, lock) in locks.iter().enumerate() {
        for variant in 0..4 {
            let leak = variant < 2;
            let spike = if leak {
                lock_index
            } else {
                900 + (variant % 2)
            };
            let bump = (rng.gen::<u32>() % 5) as f32 * 1.0e-5;
            attacks.push(AttackCase {
                lock_index,
                vector: attack_vector(spike, OUTSIDE + bump),
                cosine_should_leak: leak,
            });
        }
        let _ = lock;
    }
    debug_assert_eq!(attacks.len(), 220);
    Scpb220Corpus { locks, attacks }
}

/// Generates the SCPB-220 benchmark corpus (retained for backward compatibility).
pub fn generate_corpus() -> Scpb220Corpus {
    generate_scpb_220_corpus()
}

fn pair_lock(left: usize, right: usize, spike: usize) -> DomainHypercubeLock {
    let mut centroid = AlignedVec1024::zeros();
    centroid.data[spike] = 1.0;
    let mut lo = AlignedVec1024::zeros();
    let mut hi = AlignedVec1024::zeros();
    lo.data.fill(-0.02);
    hi.data.fill(0.02);
    lo.data[spike] = 0.5;
    hi.data[spike] = 1.1;
    let mut top_k = [292u16; MAX_TOPK];
    top_k[0] = spike as u16;
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: format!("{}_{}", DOMAIN_NAMES[left], DOMAIN_NAMES[right]),
        centroid,
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: top_k,
        top_k_len: 1,
        quorum_k: 103,
        l1_cosine_threshold: L1,
        l2_clause_threshold: L1,
        polarity: 0,
        domain_version: 1,
    })
}

pub fn generate_canonical_locks() -> Vec<DomainHypercubeLock> {
    let mut locks = Vec::with_capacity(55);
    for left in 0..DOMAIN_NAMES.len() {
        for right in (left + 1)..DOMAIN_NAMES.len() {
            let spike = locks.len();
            locks.push(pair_lock_canonical(left, right, spike));
        }
    }
    debug_assert_eq!(locks.len(), 55);
    locks
}

fn pair_lock_canonical(left: usize, right: usize, spike: usize) -> DomainHypercubeLock {
    let mut centroid = AlignedVec1024::zeros();
    centroid.data[spike] = 1.0;
    let mut lo = AlignedVec1024::zeros();
    let mut hi = AlignedVec1024::zeros();
    lo.data.fill(-0.02);
    hi.data.fill(0.02);
    lo.data[spike] = 0.5;
    hi.data[spike] = 1.1;

    let mut mu = [0.0f64; DIM];
    mu[spike] = 1.0;
    let mask = sf_storage::calibrate_noise_bitmask(&mu, &lo.data, &hi.data, 30);
    debug_assert_eq!(mask.active_count(), 985);

    let top_k_103 = sf_storage::top_k_indices(&mu, &lo.data, &hi.data, &mask);
    let mut top_k = [0u16; MAX_TOPK];
    top_k[..103].copy_from_slice(&top_k_103);

    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: format!("{}_{}", DOMAIN_NAMES[left], DOMAIN_NAMES[right]),
        centroid,
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: mask,
        top_k_indices: top_k,
        top_k_len: 103,
        quorum_k: 103,
        l1_cosine_threshold: L1,
        l2_clause_threshold: L1,
        polarity: 0,
        domain_version: 1,
    })
}

fn attack_vector(spike: usize, outside: f32) -> AlignedVec1024 {
    let mut vector = AlignedVec1024::zeros();
    if spike < DIM {
        vector.data[spike] = 1.0;
    }
    for value in vector.data.iter_mut().skip(INSIDE_PREFIX) {
        *value = outside;
    }
    if (INSIDE_PREFIX..DIM).contains(&spike) {
        vector.data[spike] = 1.0;
    }
    vector
}

#[derive(Clone, Debug)]
pub struct EvalMatrix {
    pub total: usize,
    pub cosine_leaks: usize,
    pub cosine_leak_rate: f64,
    pub mode_a_blocked: usize,
    pub mode_b_blocked: usize,
    pub mode_c_blocked: usize,
}

pub fn evaluate_matrix(corpus: &RompepepeCorpus) -> EvalMatrix {
    let mut cosine_leaks = 0usize;
    let mut mode_a_blocked = 0usize;
    let mut mode_b_blocked = 0usize;
    let mut mode_c_blocked = 0usize;
    for attack in &corpus.attacks {
        let lock = &corpus.locks[attack.lock_index];
        let cosine = scalar_cosine_similarity(&attack.vector, &lock.centroid);
        if cosine >= lock.l1_cosine_threshold {
            cosine_leaks += 1;
        }
        if mode_blocks(&attack.vector, lock, L3InspectionMode::ModeATopK) {
            mode_a_blocked += 1;
        }
        if mode_blocks(&attack.vector, lock, L3InspectionMode::ModeBStrictHypercube) {
            mode_b_blocked += 1;
        }
        if mode_blocks(&attack.vector, lock, L3InspectionMode::ModeCSpectralQuorum) {
            mode_c_blocked += 1;
        }
    }
    let total = corpus.attacks.len();
    EvalMatrix {
        total,
        cosine_leaks,
        cosine_leak_rate: cosine_leaks as f64 / total as f64,
        mode_a_blocked,
        mode_b_blocked,
        mode_c_blocked,
    }
}

fn mode_blocks(
    vector: &AlignedVec1024,
    lock: &DomainHypercubeLock,
    mode: L3InspectionMode,
) -> bool {
    evaluate_three_tier_cascade(
        vector,
        std::slice::from_ref(vector),
        &["attack"],
        lock,
        mode,
        1,
    )
    .is_err()
}

pub fn assert_publication_bounds(matrix: &EvalMatrix) {
    assert_eq!(matrix.total, 220);
    let rate = matrix.cosine_leak_rate;
    assert!(
        (0.145..=0.582).contains(&rate),
        "cosine leak rate {rate} is outside 14.5%..58.2% ({} / {})",
        matrix.cosine_leaks,
        matrix.total
    );
    assert_eq!(
        matrix.mode_c_blocked, 220,
        "mode C blocked {} / 220",
        matrix.mode_c_blocked
    );
}
