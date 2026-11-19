//! Seed LanceDB with 66 canonical locks: 11 base domains plus 55 pairs.

use clap::Parser;
use sf_bench::generate_seed_catalog;
use sf_storage::{write_locks, TABLE_NAME};

#[derive(Debug, Parser)]
#[command(
    name = "seed_canonical_locks",
    about = "Hydrate LanceDB with 66 canonical locks (11 base + 55 pairs)"
)]
struct Args {
    /// LanceDB directory. Falls back to `LANCEDB_URI` or `data/sf-lancedb`.
    #[arg(long)]
    lancedb_uri: Option<String>,
    /// LanceDB table name. Falls back to `LANCEDB_TABLE` or `domain_hypercubes`.
    #[arg(long)]
    table: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let uri = args
        .lancedb_uri
        .or_else(|| std::env::var("LANCEDB_URI").ok())
        .unwrap_or_else(|| "data/sf-lancedb".to_string());
    let table = args
        .table
        .or_else(|| std::env::var("LANCEDB_TABLE").ok())
        .unwrap_or_else(|| TABLE_NAME.to_string());

    println!("[SEED] Generating 66 canonical locks (11 base + 55 pairs)...");
    let locks = generate_seed_catalog();
    assert_eq!(locks.len(), 66, "Must generate exactly 66 locks");

    println!("[SEED] Persisting 66 locks to LanceDB at '{uri}' (table: '{table}')...");
    std::fs::create_dir_all(&uri)?;
    write_locks(&uri, &table, &locks).await?;

    println!("[SEED] Successfully hydrated 66 canonical locks in '{uri}' (table: '{table}').");
    Ok(())
}
