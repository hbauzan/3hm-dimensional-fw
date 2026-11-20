//! Standalone CLI binary entrypoint for sf-ui.
//!
//! Serves the Diagnostic Studio on `--listen` (default 127.0.0.1:3000),
//! auto-hydrating the 55 canonical locks into LanceDB if `--lancedb-uri` is omitted.

use std::sync::Arc;

use clap::Parser;
use sf_bench::{generate_canonical_locks, generate_corpus};
use sf_storage::{write_locks, HotRegistry};
use sf_ui::{router, UiAppState};
use tokio::net::TcpListener;

#[derive(Debug, Parser)]
#[command(
    name = "sf-ui",
    about = concat!("Three-Headed Semantic Firewall Diagnostic Studio v", env!("CARGO_PKG_VERSION"))
)]
pub struct CliArgs {
    /// Address and port to bind TCP listener.
    #[arg(long, default_value = "127.0.0.1:3000")]
    pub listen: String,

    /// Backing LanceDB URI. If omitted, automatically hydrates 55 canonical locks in tempdir.
    #[arg(long)]
    pub lancedb_uri: Option<String>,

    /// LanceDB table name for domain hypercube locks.
    #[arg(long, default_value = "domain_hypercubes")]
    pub lancedb_table: String,
}

#[tokio::main]
async fn main() {
    let args = CliArgs::parse();

    println!("===============================================================================");
    println!(
        "  THREE-HEADED SEMANTIC FIREWALL — DIAGNOSTIC STUDIO v{} (sf-ui)",
        env!("CARGO_PKG_VERSION")
    );
    println!("===============================================================================");

    let (registry, resolved_uri) = match &args.lancedb_uri {
        Some(uri) => {
            println!(
                "[LANCEDB] Loading existing HotRegistry from URI: {uri} (table: {})",
                args.lancedb_table
            );
            let reg = HotRegistry::load_from_lancedb(uri, &args.lancedb_table)
                .await
                .expect("Failed to load HotRegistry from LanceDB URI");
            (reg, Some(uri.clone()))
        }
        None => {
            let temp_dir =
                std::env::temp_dir().join(format!("sf-ui-lancedb-{}", std::process::id()));
            let temp_uri = temp_dir.to_string_lossy().to_string();
            println!(
                "[LANCEDB] Auto-hydrating 55 canonical locks into temporary LanceDB: {temp_uri}"
            );
            let canonical_locks = generate_canonical_locks();
            assert_eq!(
                canonical_locks.len(),
                55,
                "Canonical locks must be exactly 55"
            );
            write_locks(&temp_uri, &args.lancedb_table, &canonical_locks)
                .await
                .expect("Failed to write canonical locks to LanceDB");
            let reg = HotRegistry::load_from_lancedb(&temp_uri, &args.lancedb_table)
                .await
                .expect("Failed to load HotRegistry from hydrated LanceDB");
            (reg, Some(temp_uri))
        }
    };

    println!(
        "[REGISTRY] Loaded {} domain hypercube locks into lock-free HotRegistry.",
        registry.locks().len()
    );

    let corpus = generate_corpus();
    println!(
        "[BENCH] Generated Rompepepe corpus: {} locks, {} attack vectors.",
        corpus.locks.len(),
        corpus.attacks.len()
    );

    let state = Arc::new(UiAppState::diagnostic(
        Arc::new(registry),
        corpus,
        resolved_uri,
        args.lancedb_table,
    ));

    let app = router(state);

    let listener = TcpListener::bind(&args.listen)
        .await
        .unwrap_or_else(|err| panic!("Failed to bind TCP listener on {}: {err}", args.listen));

    let local_addr = listener
        .local_addr()
        .expect("Failed to query listener local address");
    println!("[SERVER] Diagnostic Studio listening on http://{local_addr}");
    println!("[SERVER] Ready for interactive browser inspection.");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("HTTP server terminated unexpectedly");

    println!("[SERVER] Shutdown complete.");
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C signal handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("Failed to install SIGTERM signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {
            println!("\n[SHUTDOWN] Received SIGINT (Ctrl+C), shutting down gracefully...");
        },
        _ = terminate => {
            println!("\n[SHUTDOWN] Received SIGTERM, shutting down gracefully...");
        },
    }
}
