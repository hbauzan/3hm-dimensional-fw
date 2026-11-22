//! Deterministic `fhv1` calibration against a raw-f64 embedder.

use std::path::PathBuf;

use clap::Parser;
use sf_bench::{canonical_fhv1_documents, read_corpus_path};
use sf_kernels::{Fhv1Quantiles, MovementMetric};
use sf_proxy::{calibrate_fhv1_corpus, Fhv1CalibrateSpec, TeiHttpEmbedder};
use sf_storage::{export_xlsx, load_registry, Fhv1Store, Fhv1XlsxPayload};

#[derive(Debug, Parser)]
#[command(
    name = "fhv1_calibrate",
    about = "Calibrate an fhv1 AABB profile from a corpus using raw float64 embeddings"
)]
struct Args {
    #[arg(long)]
    policy_id: String,
    #[arg(long, default_value = "data/sf-lancedb")]
    lancedb_uri: String,
    #[arg(long, default_value = "http://127.0.0.1:8080")]
    tei_http_url: String,
    /// `.txt`, `.md`, `.jsonl`, or a directory of those files. Defaults to the canonical seed.
    #[arg(long)]
    corpus: Option<PathBuf>,
    #[arg(long, default_value_t = true, action = clap::ArgAction::Set)]
    normalize: bool,
    #[arg(long, default_value_t = false, action = clap::ArgAction::Set)]
    use_rogue_mask: bool,
    #[arg(long, default_value = "variance")]
    metric: String,
    #[arg(long, default_value_t = false, action = clap::ArgAction::Set)]
    augmented_llm: bool,
    #[arg(long)]
    export_xlsx: Option<PathBuf>,
}

fn parse_metric(text: &str) -> Result<MovementMetric, String> {
    match text {
        "variance" => Ok(MovementMetric::Variance),
        "std_dev" => Ok(MovementMetric::StdDev),
        "span" => Ok(MovementMetric::Span),
        other => Err(format!(
            "unknown metric '{other}'; expected variance|std_dev|span"
        )),
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let metric = parse_metric(&args.metric)?;
    let documents = match &args.corpus {
        Some(path) => read_corpus_path(path)?,
        None => canonical_fhv1_documents(&args.policy_id)?,
    };
    if documents.is_empty() {
        return Err("fhv1 corpus is empty".into());
    }
    let before = domain_lock_count(&args.lancedb_uri).await?;
    let embedder = TeiHttpEmbedder::new(&args.tei_http_url);
    let store = Fhv1Store::new(&args.lancedb_uri);
    let profile = calibrate_fhv1_corpus(
        &store,
        &embedder,
        &Fhv1CalibrateSpec {
            policy_id: &args.policy_id,
            raw_texts: &documents,
            normalize: args.normalize,
            use_rogue_mask_default: args.use_rogue_mask,
            polarity: 0,
            model_id: "BAAI/bge-m3",
            augmented_llm: args.augmented_llm,
            metric,
            quantiles: Fhv1Quantiles::standard(),
        },
    )
    .await?;
    let after = domain_lock_count(&args.lancedb_uri).await?;
    if before != after {
        return Err(format!(
            "domain_hypercubes changed during fhv1 calibration: {before} -> {after}"
        )
        .into());
    }
    println!(
        "profile_id={} version={} samples={} domain_hypercubes={}",
        profile.profile_id, profile.version, profile.sample_count, after
    );
    if let Some(path) = &args.export_xlsx {
        let samples = store.list_samples_for_profile(&profile.profile_id).await?;
        let payload = export_xlsx(&profile, &samples, sf_storage::FHV1_XLSX_MAX_ROWS)?;
        let bytes = match payload {
            Fhv1XlsxPayload::Xlsx(bytes) | Fhv1XlsxPayload::Zip(bytes) => bytes,
        };
        if let Some(parent) = path.parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent)?;
            }
        }
        std::fs::write(path, bytes)?;
        println!("exported={}", path.display());
    }
    Ok(())
}

async fn domain_lock_count(uri: &str) -> Result<usize, String> {
    match load_registry(uri).await {
        Ok(registry) => Ok(registry.len()),
        Err(err) => {
            let rendered = err.to_string();
            if rendered.contains("not found") || rendered.contains("does not exist") {
                Ok(0)
            } else {
                Err(rendered)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use clap::Parser;
    use sf_kernels::MovementMetric;

    use super::{parse_metric, Args};

    #[test]
    fn cli_defaults_to_variance_metric_and_false_augmented_llm() {
        let defaults = Args::try_parse_from(["fhv1_calibrate", "--policy-id", "python"])
            .expect("default args");
        assert_eq!(defaults.metric, "variance");
        assert!(!defaults.augmented_llm);
        assert_eq!(
            parse_metric(&defaults.metric).expect("metric"),
            MovementMetric::Variance
        );

        let custom = Args::try_parse_from([
            "fhv1_calibrate",
            "--policy-id",
            "receta",
            "--metric",
            "std_dev",
            "--augmented-llm",
            "true",
        ])
        .expect("custom args");
        assert_eq!(
            parse_metric(&custom.metric).expect("std_dev"),
            MovementMetric::StdDev
        );
        assert!(custom.augmented_llm);
        assert_eq!(parse_metric("span").expect("span"), MovementMetric::Span);
        assert!(parse_metric("bad").is_err());
    }
}
