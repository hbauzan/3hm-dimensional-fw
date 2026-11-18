//! Gateway daemon. One process serves `/v1/chat/completions` and `/api/v1/chat`.

use std::sync::Arc;

use clap::Parser;
use sf_kernels::AlignedVec1024;
use sf_proxy::{
    router_with_cors, BatchEmbedderClient, CorsAllow, MockBatchEmbedder, ProxyAppState,
    ReqwestChatForwarder, TeiGrpcEmbedder, TeiHttpEmbedder,
};
use sf_storage::{HotRegistry, TABLE_NAME};
use tokio::net::TcpListener;

#[derive(Debug, Parser)]
#[command(name = "sf-proxy", about = "Three-Headed Semantic Firewall gateway")]
struct Args {
    /// TCP listen address. Falls back to `SF_HOST`:`SF_PORT`.
    #[arg(long)]
    listen: Option<String>,
    /// LanceDB directory. Falls back to `LANCEDB_URI`.
    #[arg(long)]
    lancedb_uri: Option<String>,
    /// LanceDB table. Falls back to `LANCEDB_TABLE`.
    #[arg(long)]
    lancedb_table: Option<String>,
    /// Embedder: `mock`, `http`, or `grpc`. Falls back to `SF_EMBEDDER`.
    #[arg(long)]
    embedder: Option<String>,
    /// TEI HTTP base. Falls back to `TEI_HTTP_URL`.
    #[arg(long)]
    tei_http_url: Option<String>,
    /// TEI gRPC URL. Falls back to `TEI_GRPC_URL`.
    #[arg(long)]
    tei_grpc_url: Option<String>,
    /// Process-wide upstream for `/v1/chat/completions`. Falls back to `UPSTREAM_LLM_BASE_URL`.
    #[arg(long)]
    upstream_base_url: Option<String>,
    /// Default domain for `/v1` when the header is omitted. Falls back to `SF_DEFAULT_DOMAIN`.
    #[arg(long)]
    default_domain: Option<String>,
    /// Breach coordinate cap. Falls back to `SF_MAX_TELEMETRY_COORDS`.
    #[arg(long)]
    max_telemetry_coords: Option<usize>,
    /// Exact browser origin. Falls back to `SF_CORS_ORIGIN`. Empty and `*` allow any origin.
    #[arg(long)]
    cors_origin: Option<String>,
}

fn env_nonempty(key: &str) -> Option<String> {
    std::env::var(key)
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn pick(flag: Option<String>, key: &str) -> Option<String> {
    flag.or_else(|| env_nonempty(key))
}

fn die(message: impl std::fmt::Display) -> ! {
    eprintln!("sf-proxy: {message}");
    std::process::exit(2);
}

#[tokio::main]
async fn main() {
    sf_proxy::load_dotenv();
    let args = Args::parse();
    let host = env_nonempty("SF_HOST").unwrap_or_else(|| "127.0.0.1".to_string());
    let port = env_nonempty("SF_PORT").unwrap_or_else(|| "8088".to_string());
    let listen = args
        .listen
        .clone()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| format!("{host}:{port}"));
    let lancedb_uri = pick(args.lancedb_uri.clone(), "LANCEDB_URI")
        .unwrap_or_else(|| die("set --lancedb-uri or LANCEDB_URI"));
    let lancedb_table =
        pick(args.lancedb_table.clone(), "LANCEDB_TABLE").unwrap_or_else(|| TABLE_NAME.to_string());
    let embedder_kind =
        pick(args.embedder.clone(), "SF_EMBEDDER").unwrap_or_else(|| "mock".to_string());
    let upstream_base = pick(args.upstream_base_url.clone(), "UPSTREAM_LLM_BASE_URL")
        .unwrap_or_else(|| "http://127.0.0.1:11434".to_string());
    let default_domain = pick(args.default_domain.clone(), "SF_DEFAULT_DOMAIN")
        .unwrap_or_else(|| "python".to_string());
    let max_telemetry_coords = match args.max_telemetry_coords {
        Some(value) => value,
        None => match env_nonempty("SF_MAX_TELEMETRY_COORDS") {
            Some(raw) => raw
                .parse()
                .unwrap_or_else(|_| die("SF_MAX_TELEMETRY_COORDS is not an integer")),
            None => 8,
        },
    };
    let cors_raw = args
        .cors_origin
        .clone()
        .or_else(|| std::env::var("SF_CORS_ORIGIN").ok());
    let cors = CorsAllow::parse(cors_raw.as_deref()).unwrap_or_else(|err| die(err));

    let registry = HotRegistry::load_from_lancedb(&lancedb_uri, &lancedb_table)
        .await
        .unwrap_or_else(|err| die(format!("LanceDB load failed: {err}")));
    if registry.locks().is_empty() {
        die(format!(
            "LanceDB table '{lancedb_table}' at '{lancedb_uri}' has no DomainHypercubeLock rows"
        ));
    }
    let pass_vector = registry
        .get(&default_domain)
        .or_else(|| registry.locks().into_iter().next())
        .map(|lock| lock.centroid)
        .unwrap_or_else(|| die("registry returned no lock after the empty check"));

    let embedder: Arc<dyn BatchEmbedderClient> = match embedder_kind.as_str() {
        "mock" => {
            let centroids = registry
                .locks()
                .iter()
                .map(|lock| (lock.domain_id.clone(), lock.centroid))
                .collect();
            Arc::new(MockBatchEmbedder {
                pass_vector,
                breach_vector: AlignedVec1024::zeros(),
                centroids,
            })
        }
        "http" => {
            let url = pick(args.tei_http_url.clone(), "TEI_HTTP_URL")
                .unwrap_or_else(|| die("SF_EMBEDDER=http requires --tei-http-url or TEI_HTTP_URL"));
            Arc::new(TeiHttpEmbedder::new(url))
        }
        "grpc" => {
            let url = pick(args.tei_grpc_url.clone(), "TEI_GRPC_URL")
                .unwrap_or_else(|| die("SF_EMBEDDER=grpc requires --tei-grpc-url or TEI_GRPC_URL"));
            Arc::new(
                TeiGrpcEmbedder::connect(url)
                    .await
                    .unwrap_or_else(|err| die(format!("TEI gRPC connect failed: {err}"))),
            )
        }
        other => die(format!("unknown SF_EMBEDDER '{other}' (mock, http, grpc)")),
    };

    let state = Arc::new(ProxyAppState {
        registry: Arc::new(registry),
        embedder,
        upstream: Arc::new(ReqwestChatForwarder::new(upstream_base)),
        mock_upstream: Arc::new(sf_proxy::MockUpstreamForwarder),
        default_domain,
        max_telemetry_coords,
    });
    let app = router_with_cors(state, cors);
    let listener = TcpListener::bind(&listen)
        .await
        .unwrap_or_else(|err| die(format!("bind {listen} failed: {err}")));
    let local = listener
        .local_addr()
        .unwrap_or_else(|err| die(format!("local_addr failed: {err}")));
    println!("sf-proxy listening on http://{local}");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .unwrap_or_else(|err| die(format!("server stopped: {err}")));
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("install Ctrl+C handler");
    };
    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("install SIGTERM handler")
            .recv()
            .await;
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();
    tokio::select! {
        _ = ctrl_c => {}
        _ = terminate => {}
    }
}
