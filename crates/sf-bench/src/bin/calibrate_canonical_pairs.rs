//! Embed the eleven canonical corpora and write 11 domain locks plus 55 pairwise locks.

use clap::Parser;
use sf_bench::canonical_seed_corpus;
use sf_proxy::{BatchEmbedderClient, TeiHttpEmbedder};
use sf_storage::{assemble_canonical_catalog, write_locks_with_manifests, CANONICAL_DOMAINS, DIM};

#[derive(Debug, Parser)]
#[command(
    name = "calibrate_canonical_pairs",
    about = "Calibrate 11 domain locks and 55 pairwise differential locks with BAAI/bge-m3"
)]
struct Args {
    #[arg(long, default_value = "http://127.0.0.1:8080")]
    tei_url: String,
    #[arg(long, default_value = "data/sf-lancedb")]
    lancedb_uri: String,
    #[arg(long, default_value = "domain_hypercubes")]
    table: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let corpus = canonical_seed_corpus();
    if corpus.len() != CANONICAL_DOMAINS.len() {
        return Err("canonical seed corpus is missing a domain".into());
    }
    println!(
        "[CALIBRATE] Connecting to TEI at {} for {} domains...",
        args.tei_url,
        corpus.len()
    );
    let embedder = TeiHttpEmbedder::new(&args.tei_url);
    let mut owned_rows: Vec<(String, Vec<f32>)> = Vec::with_capacity(corpus.len());
    for entry in corpus {
        let mut flat = Vec::with_capacity(entry.sentences.len() * DIM);
        for batch in entry.sentences.chunks(8) {
            let vectors = embedder.embed_batch_f32(batch).await?;
            if vectors.len() != batch.len() {
                return Err(format!(
                    "fail-closed: TEI returned {} vectors for {} sentences in {}",
                    vectors.len(),
                    batch.len(),
                    entry.domain_id
                )
                .into());
            }
            for vector in vectors {
                flat.extend_from_slice(&vector.data);
            }
        }
        println!(
            "[CALIBRATE] Embedded {} sentences for {}",
            entry.sentences.len(),
            entry.domain_id
        );
        owned_rows.push((entry.domain_id.to_string(), flat));
    }
    let borrowed: Vec<(&str, &[f32])> = owned_rows
        .iter()
        .map(|(name, rows)| (name.as_str(), rows.as_slice()))
        .collect();
    let catalog = assemble_canonical_catalog(&borrowed).map_err(|err| err.to_string())?;
    let pairs = catalog
        .locks
        .iter()
        .filter(|lock| lock.domain_id.contains('_'))
        .count();
    let domains = catalog.locks.len() - pairs;
    println!("[CALIBRATE] Built {domains} domain locks and {pairs} pairwise locks");
    write_locks_with_manifests(
        &args.lancedb_uri,
        &args.table,
        &catalog.locks,
        &catalog.manifests,
    )
    .await?;
    println!(
        "[CALIBRATE] Wrote {} locks to {} table {}",
        catalog.locks.len(),
        args.lancedb_uri,
        args.table
    );
    Ok(())
}
