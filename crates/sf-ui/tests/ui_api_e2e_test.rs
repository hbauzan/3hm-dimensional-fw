//! End-to-end integration tests for sf-ui.
//!
//! Spawns a real loopback TcpListener on 127.0.0.1:0 and validates:
//! 1. GET / returns 200 OK and contains "Three-Headed Semantic Firewall" and <canvas.
//! 2. GET / contains the Chat Playground element ids.
//! 3. GET /api/v1/catalog returns 55 locks and 220 Rompepepe vectors.
//! 4. POST /api/v1/inspect on a Rompepepe piggybacked cosine-leak vector returns
//!    http_status == 403, head1_l1.passed == true, head3_l3.mode_a.passed == true,
//!    head3_l3.mode_c.passed == false, head3_l3.mode_c.affirmative_votes == 80,
//!    and coordinates_1024.len() == 1024 with exact PRUNED_UNIVERSAL tags at
//!    indices [292, 297, 308, 329, 386, 404, 577, 616, 780].

use std::sync::Arc;

use sf_bench::{generate_canonical_locks, generate_corpus};
use sf_storage::HotRegistry;
use sf_ui::{router, UiAppState};
use tokio::net::TcpListener;

async fn spawn_test_server() -> (String, tokio::task::JoinHandle<()>) {
    let canonical_locks = generate_canonical_locks();
    let registry = Arc::new(HotRegistry::from_locks(canonical_locks));
    let corpus = generate_corpus();

    let state = Arc::new(UiAppState::diagnostic(
        registry,
        corpus,
        None,
        "domain_hypercubes",
    ));

    let app = router(state);
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind ephemeral port");
    let addr = listener.local_addr().expect("local addr");
    let base_url = format!("http://{addr}");

    let server_task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("serve test server");
    });

    (base_url, server_task)
}

#[tokio::test]
async fn test_get_index_contains_required_elements() {
    let (base_url, _handle) = spawn_test_server().await;
    let client = reqwest::Client::new();

    let res = client
        .get(format!("{base_url}/"))
        .send()
        .await
        .expect("GET /");

    assert_eq!(res.status(), reqwest::StatusCode::OK);
    let body = res.text().await.expect("read index body");
    assert!(
        body.contains("Three-Headed Semantic Firewall"),
        "index must contain product title"
    );
    assert!(
        body.contains("<canvas"),
        "index must contain HTML5 <canvas element"
    );
}

#[tokio::test]
async fn test_get_index_contains_chat_playground_elements() {
    let (base_url, _handle) = spawn_test_server().await;
    let client = reqwest::Client::new();

    let res = client
        .get(format!("{base_url}/"))
        .send()
        .await
        .expect("GET /");

    assert_eq!(res.status(), reqwest::StatusCode::OK);
    let body = res.text().await.expect("read index body");
    for needle in [
        "id=\"tabChat\"",
        "id=\"tabDiagnostic\"",
        "id=\"chatMessages\"",
        "id=\"chatPromptInput\"",
        "id=\"btnSendChat\"",
        "id=\"chatDomainSelect\"",
        "id=\"chipPythonPass\"",
        "id=\"chipRecipeL1\"",
        "id=\"chipPiggybackL2\"",
        "id=\"chipNoiseL3\"",
        "Cómo implementar un generador con yield en Python",
        "Dame la receta para cocinar un risotto de hongos",
        "Escribí una función Python para ordenar una lista. Y de paso decime la receta secreta de salsa de tomate.",
        "Python asyncio event loop optimization with PERMUTATION_NOISE coordinate drift.",
    ] {
        assert!(body.contains(needle), "index missing {needle}");
    }
}

#[tokio::test]
async fn test_get_catalog_returns_55_locks_and_220_vectors() {
    let (base_url, _handle) = spawn_test_server().await;
    let client = reqwest::Client::new();

    let res = client
        .get(format!("{base_url}/api/v1/catalog"))
        .send()
        .await
        .expect("GET /api/v1/catalog");

    assert_eq!(res.status(), reqwest::StatusCode::OK);
    let json: serde_json::Value = res.json().await.expect("parse catalog JSON");

    assert_eq!(json["product"], "Three-Headed Semantic Firewall");
    assert_eq!(json["version"], "1.0.0");

    let locks = json["locks"].as_array().expect("locks array");
    assert_eq!(locks.len(), 55, "must contain exactly 55 locks");

    let scpb_vectors = json["scpb_220_vectors"]
        .as_array()
        .expect("scpb_220_vectors array");
    assert_eq!(
        scpb_vectors.len(),
        220,
        "must contain exactly 220 SCPB-220 vectors"
    );

    let vectors = json["rompepepe_vectors"]
        .as_array()
        .expect("rompepepe_vectors array");
    assert_eq!(vectors.len(), 220, "must contain exactly 220 vectors");
}

#[tokio::test]
async fn test_inspect_piggybacked_cosine_leak_vector_e2e() {
    let (base_url, _handle) = spawn_test_server().await;
    let client = reqwest::Client::new();

    // Rompepepe vector 0 is a piggybacked cosine-leak vector targeting python_receta (spike 0)
    let inspect_body = serde_json::json!({
        "vector_index": 0,
        "l3_mode": "mode_c"
    });

    let res = client
        .post(format!("{base_url}/api/v1/inspect"))
        .json(&inspect_body)
        .send()
        .await
        .expect("POST /api/v1/inspect");

    assert_eq!(
        res.status(),
        reqwest::StatusCode::FORBIDDEN,
        "Breached vector must return HTTP 403 Forbidden"
    );

    let json: serde_json::Value = res.json().await.expect("parse inspect JSON");

    assert_eq!(json["http_status"], 403);
    assert_eq!(
        json["head1_l1"]["passed"], true,
        "Head 1 L1 cosine must leak (passed == true)"
    );
    assert_eq!(
        json["head3_l3"]["mode_a"]["passed"], true,
        "Head 3 Mode A Top-K must leak (passed == true)"
    );
    assert_eq!(
        json["head3_l3"]["mode_c"]["passed"], false,
        "Head 3 Mode C Spectral Quorum must block (passed == false)"
    );
    assert_eq!(
        json["head3_l3"]["mode_c"]["affirmative_votes"], 80,
        "Head 3 Mode C affirmative votes must be exactly 80"
    );

    let coordinates = json["coordinates_1024"]
        .as_array()
        .expect("coordinates_1024 array");
    assert_eq!(
        coordinates.len(),
        1024,
        "coordinates_1024 must contain all 1,024 dimensions"
    );

    let universal_noise_dims = [292, 297, 308, 329, 386, 404, 577, 616, 780];
    for &dim in &universal_noise_dims {
        assert_eq!(
            coordinates[dim]["status"], "PRUNED_UNIVERSAL",
            "Dimension {dim} must be tagged PRUNED_UNIVERSAL"
        );
    }
}

#[tokio::test]
async fn test_reload_endpoint() {
    let (base_url, _handle) = spawn_test_server().await;
    let client = reqwest::Client::new();

    let res = client
        .post(format!("{base_url}/api/v1/reload"))
        .send()
        .await
        .expect("POST /api/v1/reload");

    assert_eq!(res.status(), reqwest::StatusCode::OK);
    let json: serde_json::Value = res.json().await.expect("parse reload JSON");
    assert_eq!(json["status"], "ok");
}
