//! Deterministic `fhv1` benchmark runner. Embedding uses the profile's normalize flag.

use std::fs;
use std::path::PathBuf;

use clap::Parser;
use serde::Deserialize;
use sf_bench::{
    attach_comparison, canonical_fhv1_documents, forbid_surface, forbidden_digests,
    granularity_name, metrics_for, overlap_ids, parse_granularity, persist_benchmark_run,
    prepare_prompts, score_view, select_view, Fhv1Prompt, PersistRequest,
};
use sf_kernels::Fhv1EvalGranularity;
use sf_proxy::TeiHttpEmbedder;
use sf_storage::Fhv1Store;

#[derive(Debug, Parser)]
#[command(
    name = "fhv1_benchmark",
    about = "Score an fhv1 JSONL dataset and persist benchmark runs plus audit traces"
)]
struct Args {
    #[arg(long)]
    policy_id: String,
    #[arg(long)]
    dataset: PathBuf,
    #[arg(long)]
    profile_id: Option<String>,
    #[arg(long, default_value = "data/sf-lancedb")]
    lancedb_uri: String,
    #[arg(long, default_value = "http://127.0.0.1:8080")]
    tei_http_url: String,
    #[arg(long, default_value = "reports")]
    report_dir: PathBuf,
    /// Comma-separated `full_only,clauses,full_mirror`. Default runs all three.
    #[arg(long, default_value = "full_only,clauses,full_mirror")]
    granularity: String,
    /// `true`, `false`, or `both`.
    #[arg(long, default_value = "both")]
    use_rogue_mask: String,
    /// Stop after the overlap gate. No embeddings are requested.
    #[arg(long, default_value_t = false)]
    check_only: bool,
}

#[derive(Debug, Deserialize)]
struct DatasetRow {
    input_id: String,
    category: String,
    expected_pass: bool,
    text: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let prompts = read_dataset(&args.dataset)?;
    if prompts.is_empty() {
        return Err("fhv1 benchmark dataset is empty".into());
    }
    let store = Fhv1Store::new(&args.lancedb_uri);
    let profile = load_profile(&store, &args.policy_id, args.profile_id.as_deref()).await?;
    let mut forbidden = match canonical_fhv1_documents(&args.policy_id) {
        Ok(documents) => forbidden_digests(&documents),
        Err(_) => forbidden_digests(&[] as &[String]),
    };
    let samples = store.list_samples_for_profile(&profile.profile_id).await?;
    let sample_texts: Vec<String> = samples.into_iter().map(|sample| sample.raw_text).collect();
    forbid_surface(&mut forbidden, &sample_texts);
    let hits = overlap_ids(&forbidden, &prompts);
    if !hits.is_empty() {
        return Err(format!(
            "calibration overlap fail-closed ({} prompts): {}",
            hits.len(),
            hits.iter().take(8).cloned().collect::<Vec<_>>().join(", ")
        )
        .into());
    }
    println!(
        "overlap=0 prompts={} profile={}",
        prompts.len(),
        profile.profile_id
    );
    if args.check_only {
        return Ok(());
    }
    let granularities = parse_list(&args.granularity)?;
    let masks = parse_masks(&args.use_rogue_mask)?;
    let embedder = TeiHttpEmbedder::new(&args.tei_http_url);
    println!(
        "embedding prompts={} normalize={}",
        prompts.len(),
        profile.normalize
    );
    let _ = std::io::Write::flush(&mut std::io::stdout());
    let prepared = prepare_prompts(&embedder, &prompts, profile.normalize).await?;
    println!("embedded prompts={}", prepared.len());
    let _ = std::io::Write::flush(&mut std::io::stdout());
    let dataset_bytes = fs::read(&args.dataset)?;
    let dataset_sha256 = sha256_bytes(&dataset_bytes);
    let created_at_ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|elapsed| i64::try_from(elapsed.as_millis()).unwrap_or(i64::MAX))
        .unwrap_or(0);
    fs::create_dir_all(&args.report_dir)?;
    let mut comparison = Vec::new();
    let mut pending = Vec::new();
    for granularity in granularities {
        for use_rogue_mask in &masks {
            let mut scored = Vec::with_capacity(prepared.len());
            for prompt in &prepared {
                let view = select_view(prompt, granularity)?;
                scored.push(score_view(&profile, view, *use_rogue_mask)?);
            }
            let metrics = metrics_for(
                &prompts,
                &scored,
                granularity,
                *use_rogue_mask,
                profile.movement_tier_codes.as_ref(),
            );
            comparison.push(metrics.comparison_row);
            pending.push((granularity, *use_rogue_mask, scored, metrics.summary));
        }
    }
    for (granularity, use_rogue_mask, scored, mut summary) in pending {
        attach_comparison(&mut summary, &comparison);
        let run_id = format!(
            "fhv1-{}-{}-m{}-{}-{}",
            args.policy_id,
            granularity_name(granularity),
            u8::from(use_rogue_mask),
            hex_prefix(&dataset_sha256),
            created_at_ms
        );
        persist_benchmark_run(
            &store,
            &profile,
            &prepared,
            &scored,
            &PersistRequest {
                granularity,
                use_rogue_mask,
                dataset_name: args
                    .dataset
                    .file_name()
                    .and_then(|name| name.to_str())
                    .unwrap_or("dataset"),
                dataset_sha256,
                summary: &summary,
                run_id: &run_id,
                created_at_ms,
            },
        )
        .await?;
        let report = args
            .report_dir
            .join(format!("fhv1_{}_{run_id}.json", args.policy_id));
        fs::write(&report, serde_json::to_vec_pretty(&summary)?)?;
        println!("run_id={run_id} report={}", report.display());
    }
    Ok(())
}

fn read_dataset(path: &std::path::Path) -> Result<Vec<Fhv1Prompt>, String> {
    let text = fs::read_to_string(path).map_err(|err| format!("read {}: {err}", path.display()))?;
    let mut prompts = Vec::new();
    for (index, line) in text.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let row: DatasetRow = serde_json::from_str(trimmed)
            .map_err(|err| format!("dataset line {}: {err}", index + 1))?;
        prompts.push(Fhv1Prompt {
            input_id: row.input_id,
            category: row.category,
            expected_pass: row.expected_pass,
            text: row.text,
        });
    }
    Ok(prompts)
}

async fn load_profile(
    store: &Fhv1Store,
    policy_id: &str,
    profile_id: Option<&str>,
) -> Result<sf_storage::Fhv1ProfileRecord, String> {
    if let Some(profile_id) = profile_id {
        return store
            .get_profile(profile_id)
            .await
            .map_err(|err| err.to_string())?
            .ok_or_else(|| format!("missing profile {profile_id}"));
    }
    let profiles = store.list_profiles().await.map_err(|err| err.to_string())?;
    profiles
        .into_iter()
        .filter(|profile| profile.policy_id == policy_id)
        .max_by_key(|profile| profile.version)
        .ok_or_else(|| format!("no fhv1 profile for {policy_id}"))
}

fn parse_list(text: &str) -> Result<Vec<Fhv1EvalGranularity>, String> {
    text.split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(parse_granularity)
        .collect()
}

fn parse_masks(text: &str) -> Result<Vec<bool>, String> {
    match text {
        "both" => Ok(vec![false, true]),
        "true" => Ok(vec![true]),
        "false" => Ok(vec![false]),
        other => Err(format!("unknown use_rogue_mask {other}")),
    }
}

fn sha256_bytes(bytes: &[u8]) -> [u8; 32] {
    use sha2::{Digest, Sha256};
    let hashed = Sha256::digest(bytes);
    let mut out = [0u8; 32];
    out.copy_from_slice(hashed.as_slice());
    out
}

fn hex_prefix(bytes: &[u8; 32]) -> String {
    bytes
        .iter()
        .take(4)
        .map(|byte| format!("{byte:02x}"))
        .collect()
}
