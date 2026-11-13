use sf_kernels::{
    evaluate_l3_gate, AlignedVec1024, DomainHypercubeLock, L3InspectionMode, LockSpec,
    NoiseBitmask1024, DIM, MAX_TOPK,
};
use sf_storage::{
    calibrate_pairwise_lock, load_registry, manifest_from_matrices, write_locks_with_manifests,
    HotRegistry,
};

fn lock(domain_id: &str) -> DomainHypercubeLock {
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: domain_id.to_string(),
        centroid: AlignedVec1024::zeros(),
        lo: AlignedVec1024::zeros(),
        hi: AlignedVec1024::zeros(),
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: [0u16; MAX_TOPK],
        top_k_len: 1,
        quorum_k: 103,
        l1_cosine_threshold: 0.5,
        l2_clause_threshold: 0.5,
        polarity: 0,
        domain_version: 1,
    })
}

#[test]
fn hot_registry_returns_the_ten_pairs_that_touch_a_canonical_domain() {
    let registry = HotRegistry::from_locks([
        lock("python"),
        lock("receta"),
        lock("python_receta"),
        lock("legal_python"),
        lock("arquitectura_python"),
        lock("astronomia_python"),
        lock("botanica_python"),
        lock("filosofia_python"),
        lock("finanzas_python"),
        lock("geologia_python"),
        lock("medicina_python"),
        lock("musica_python"),
        lock("legal_receta"),
    ]);
    let python = registry.pairwise_locks_for("python");
    let ids: Vec<&str> = python.iter().map(|item| item.domain_id.as_str()).collect();
    assert_eq!(
        ids,
        vec![
            "arquitectura_python",
            "astronomia_python",
            "botanica_python",
            "filosofia_python",
            "finanzas_python",
            "geologia_python",
            "legal_python",
            "medicina_python",
            "musica_python",
            "python_receta",
        ]
    );
    assert!(registry.pairwise_locks_for("python_receta").is_empty());
    let receta_locks = registry.pairwise_locks_for("receta");
    let receta: Vec<&str> = receta_locks
        .iter()
        .map(|item| item.domain_id.as_str())
        .collect();
    assert_eq!(receta, vec!["legal_receta", "python_receta"]);
}

fn separated_row(head: f32, head_len: usize, tail: f32) -> Vec<f32> {
    let mut row = vec![tail; DIM];
    for value in row.iter_mut().take(head_len) {
        *value = head;
    }
    row
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn pairwise_lock_with_fewer_than_103_dims_roundtrips_without_duplicate_votes() {
    let mut left = separated_row(1.0, 20, 0.0);
    let mut right = separated_row(-1.0, 20, 0.0);
    left[292] = 4.0;
    right[292] = -4.0;
    let lock = calibrate_pairwise_lock("legal", "python", &left, &right).expect("pair");
    assert_eq!(lock.top_k_len, 20);
    let manifest = manifest_from_matrices(&[&left, &right]).expect("manifest");
    assert_eq!(manifest.doc_count, 2);
    assert_ne!(manifest.sha256, [0u8; 32]);
    let dir = std::env::temp_dir().join(format!("sf-pair-topk-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let uri = dir.to_str().unwrap();
    write_locks_with_manifests(
        uri,
        "domain_hypercubes",
        std::slice::from_ref(&lock),
        std::slice::from_ref(&manifest),
    )
    .await
    .unwrap();
    let registry = load_registry(uri).await.unwrap();
    let stored = registry.get("legal_python").expect("pair row");
    assert_eq!(stored.top_k_len, lock.top_k_len);
    assert_eq!(registry.manifest("legal_python"), Some(manifest));
    let mut seen = [false; DIM];
    for index in stored
        .top_k_indices
        .iter()
        .take(usize::from(stored.top_k_len))
    {
        let dim = usize::from(*index);
        assert!(!seen[dim], "duplicate coordinate {dim}");
        seen[dim] = true;
    }
    let query = AlignedVec1024::from_slice(&left).expect("1024");
    let gate = evaluate_l3_gate(&query, &stored, L3InspectionMode::ModeATopK, 0);
    assert_eq!(gate.evaluated_dimensions, 20);
    assert_eq!(gate.affirmative_votes, 20);
    let _ = std::fs::remove_dir_all(&dir);
}
