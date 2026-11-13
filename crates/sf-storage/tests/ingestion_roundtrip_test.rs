use rand::Rng;
use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;
use sf_kernels::{
    evaluate_l3_gate, AlignedVec1024, DomainHypercubeLock, L3InspectionMode, LockSpec,
    NoiseBitmask1024, DEFAULT_QUORUM_K, DIM, MAX_TOPK,
};
use sf_storage::{
    calibrate_matrix, calibrate_noise_bitmask, load_registry, record_batch_from_locks,
    write_calibration, write_locks, write_locks_with_manifests, CorpusManifest, DomainRegistry,
    IngestSpec,
};

#[test]
fn extra_pruned_dims_reaches_985_active() {
    let mu = [0.01f64; DIM];
    let lo = [0.0f32; DIM];
    let hi = [1.0f32; DIM];
    let mask = calibrate_noise_bitmask(&mu, &lo, &hi, 30);
    assert_eq!(mask.active_count(), 985);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn five_hundred_vectors_roundtrip_lo_bits() {
    let mut rng = ChaCha8Rng::seed_from_u64(0x1A4C_E500);
    let mut rows = vec![0.0f32; 500 * DIM];
    for value in &mut rows {
        *value = rng.gen::<f32>() * 0.02 - 0.01;
    }
    let calibration = calibrate_matrix(&rows, 0).unwrap();
    let dir = std::env::temp_dir().join(format!("sf-lance-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let uri = dir.to_str().unwrap();
    write_calibration(IngestSpec {
        uri,
        domain_id: "python",
        version: 1,
        polarity: 0,
        l1: 0.4,
        l2: 0.35,
        epsilon: 0.0,
        quorum_k: 103,
        calibration: &calibration,
    })
    .await
    .unwrap();
    let registry = load_registry(uri).await.unwrap();
    let lock = registry.get("python").unwrap();
    assert_eq!(lock.top_k_len, calibration.top_k_len);
    assert_eq!(registry.manifest("python"), Some(calibration.manifest()));
    assert_eq!(calibration.rows, 500);
    assert_ne!(calibration.sha256, [0u8; 32]);
    for dim in 0..DIM {
        assert_eq!(
            lock.lo_dilated.data[dim].to_bits(),
            calibration.lo[dim].to_bits(),
            "lo dim {dim}"
        );
        assert_eq!(
            lock.hi_dilated.data[dim].to_bits(),
            calibration.hi[dim].to_bits(),
            "hi dim {dim}"
        );
    }
    let _ = std::fs::remove_dir_all(&dir);
}

fn short_topk_lock(len: u16) -> DomainHypercubeLock {
    let len_us = usize::from(len);
    let mut top_k_indices = [0u16; MAX_TOPK];
    for (slot, index) in top_k_indices.iter_mut().enumerate().take(len_us) {
        *index = u16::try_from(slot).unwrap();
    }
    for index in top_k_indices
        .iter_mut()
        .take(usize::from(DEFAULT_QUORUM_K))
        .skip(len_us)
    {
        *index = 0;
    }
    let lo = AlignedVec1024::zeros();
    let mut hi = AlignedVec1024::zeros();
    hi.data[0] = 1.0;
    for dim in 1..DIM {
        hi.data[dim] = 0.1;
    }
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: "python_receta".to_string(),
        centroid: AlignedVec1024::zeros(),
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::all_active(),
        top_k_indices,
        top_k_len: len,
        quorum_k: len,
        l1_cosine_threshold: 0.5,
        l2_clause_threshold: 0.5,
        polarity: 0,
        domain_version: 1,
    })
}

fn query_inside_only_first_coordinate() -> AlignedVec1024 {
    let mut query = AlignedVec1024::zeros();
    query.data[0] = 0.5;
    for value in query.data.iter_mut().skip(1) {
        *value = 2.0;
    }
    query
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn top_k_len_27_roundtrip_scores_each_dim_once() {
    let lock = short_topk_lock(27);
    let dir = std::env::temp_dir().join(format!("sf-topk27-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let uri = dir.to_str().unwrap();
    write_locks(uri, "domain_hypercubes", &[lock])
        .await
        .unwrap();
    let registry = load_registry(uri).await.unwrap();
    let stored = registry.get("python_receta").unwrap();
    assert_eq!(stored.top_k_len, 27);
    let mut seen = [false; DIM];
    for index in stored
        .top_k_indices
        .iter()
        .take(usize::from(stored.top_k_len))
    {
        let dim = usize::from(*index);
        assert!(dim < DIM);
        assert!(!seen[dim], "duplicate coordinate {dim}");
        seen[dim] = true;
    }
    let gate = evaluate_l3_gate(
        &query_inside_only_first_coordinate(),
        &stored,
        L3InspectionMode::ModeATopK,
        0,
    );
    assert_eq!(gate.evaluated_dimensions, 27);
    assert_eq!(gate.affirmative_votes, 1);
    assert_eq!(
        registry.manifest("python_receta"),
        Some(CorpusManifest::UNPROVIDED)
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn explicit_corpus_manifest_roundtrips_with_top_k_len() {
    let lock = short_topk_lock(27);
    let manifest = CorpusManifest {
        doc_count: 42,
        sha256: [0xAB; 32],
    };
    let dir = std::env::temp_dir().join(format!("sf-manifest-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let uri = dir.to_str().unwrap();
    write_locks_with_manifests(uri, "domain_hypercubes", &[lock], &[manifest])
        .await
        .unwrap();
    let registry = load_registry(uri).await.unwrap();
    let stored = registry.get("python_receta").unwrap();
    assert_eq!(stored.top_k_len, 27);
    assert_eq!(registry.manifest("python_receta"), Some(manifest));
    let gate = evaluate_l3_gate(
        &query_inside_only_first_coordinate(),
        &stored,
        L3InspectionMode::ModeATopK,
        0,
    );
    assert_eq!(gate.evaluated_dimensions, 27);
    assert_eq!(gate.affirmative_votes, 1);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn legacy_batch_without_top_k_len_keeps_manifest_and_list_width() {
    let lock = short_topk_lock(27);
    let manifest = CorpusManifest {
        doc_count: 9,
        sha256: [0x11; 32],
    };
    let mut batch =
        record_batch_from_locks(std::slice::from_ref(&lock), std::slice::from_ref(&manifest))
            .unwrap();
    let index = batch.schema().index_of("top_k_len").unwrap();
    let _removed = batch.remove_column(index);
    let registry = DomainRegistry::from_record_batches(vec![batch]).unwrap();
    let stored = registry.get("python_receta").unwrap();
    assert_eq!(stored.top_k_len, DEFAULT_QUORUM_K);
    assert_eq!(registry.manifest("python_receta"), Some(manifest));
}
