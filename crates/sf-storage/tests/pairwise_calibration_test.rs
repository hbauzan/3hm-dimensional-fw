use sf_kernels::{evaluate_l3_gate, AlignedVec1024, L3InspectionMode, DIM};
use sf_storage::{
    assemble_canonical_catalog, assemble_canonical_locks, calibrate_pairwise_lock, load_registry,
    write_locks_with_manifests, CANONICAL_DOMAINS,
};

fn flat(rows: &[Vec<f32>]) -> Vec<f32> {
    let mut out = Vec::with_capacity(rows.len() * DIM);
    for row in rows {
        assert_eq!(row.len(), DIM);
        out.extend_from_slice(row);
    }
    out
}

fn separated_row(head: f32, head_len: usize, tail: f32) -> Vec<f32> {
    let mut row = vec![tail; DIM];
    for value in row.iter_mut().take(head_len) {
        *value = head;
    }
    row
}

fn vector_from(row: &[f32]) -> AlignedVec1024 {
    AlignedVec1024::from_slice(row).expect("1024")
}

#[test]
fn pairwise_lock_uses_lexicographic_id_and_smaller_domain_envelope() {
    let python = flat(&[separated_row(1.0, 200, 0.1), separated_row(1.0, 200, 0.1)]);
    let receta = flat(&[separated_row(-1.0, 200, 0.1), separated_row(-1.0, 200, 0.1)]);
    let lock = calibrate_pairwise_lock("receta", "python", &receta, &python).expect("pair");
    assert_eq!(lock.domain_id, "python_receta");
    assert_eq!(lock.lo_dilated.data[0].to_bits(), 1.0f32.to_bits());
    assert_eq!(lock.hi_dilated.data[0].to_bits(), 1.0f32.to_bits());
    assert_eq!(lock.quorum_k, 103);
    assert_eq!(lock.noise_mask.active_count(), 103);
    assert!(lock.noise_mask.is_active(0));
    assert!(lock.noise_mask.is_active(102));
    assert!(!lock.noise_mask.is_active(103));
    assert!(!lock.noise_mask.is_active(199));
    assert!(!lock.noise_mask.is_active(500));
    assert!(!lock.noise_mask.is_active(292));

    let norm = (200.0f64 * 4.0).sqrt();
    let expected = (2.0 / norm) as f32;
    assert!((lock.centroid.data[0] - expected).abs() < 1.0e-5);
    assert_eq!(lock.centroid.data[500].to_bits(), 0.0f32.to_bits());

    let python_vec = vector_from(&separated_row(1.0, 200, 0.1));
    let receta_vec = vector_from(&separated_row(-1.0, 200, 0.1));
    let allow = evaluate_l3_gate(&python_vec, &lock, L3InspectionMode::ModeCSpectralQuorum, 0);
    assert!(
        allow.passed,
        "{}/{}",
        allow.affirmative_votes, allow.required_votes
    );
    let deny = evaluate_l3_gate(&receta_vec, &lock, L3InspectionMode::ModeCSpectralQuorum, 0);
    assert!(!deny.passed);
    assert_eq!(deny.affirmative_votes, 0);

    let mut flipped = lock.clone();
    flipped.polarity = 1;
    let receta_as_target = evaluate_l3_gate(
        &receta_vec,
        &flipped,
        L3InspectionMode::ModeCSpectralQuorum,
        0,
    );
    assert!(receta_as_target.passed);
    let python_as_other = evaluate_l3_gate(
        &python_vec,
        &flipped,
        L3InspectionMode::ModeCSpectralQuorum,
        0,
    );
    assert!(!python_as_other.passed);
}

#[test]
fn short_discriminative_set_uses_tenth_quorum_and_drops_universal_noise() {
    let mut left = separated_row(1.0, 20, 0.0);
    let mut right = separated_row(-1.0, 20, 0.0);
    left[292] = 4.0;
    right[292] = -4.0;
    let lock = calibrate_pairwise_lock("legal", "python", &left, &right).expect("pair");
    assert_eq!(lock.domain_id, "legal_python");
    assert_eq!(lock.noise_mask.active_count(), 20);
    assert_eq!(lock.quorum_k, 2);
    assert!(!lock.noise_mask.is_active(292));
    assert!(lock.noise_mask.is_active(0));
    assert!(lock.noise_mask.is_active(19));
    assert!(!lock.noise_mask.is_active(20));
}

#[test]
fn identical_domains_fail_closed_with_an_empty_mask() {
    let row = vec![0.25f32; DIM];
    let lock = calibrate_pairwise_lock("musica", "filosofia", &row, &row).expect("pair");
    assert_eq!(lock.noise_mask.active_count(), 0);
    assert_eq!(lock.quorum_k, 1);
    let sample = vector_from(&row);
    let gate = evaluate_l3_gate(&sample, &lock, L3InspectionMode::ModeCSpectralQuorum, 0);
    assert!(!gate.passed);
}

#[test]
fn rejects_unknown_domains_and_empty_matrices() {
    let row = vec![0.0f32; DIM];
    let err = calibrate_pairwise_lock("python", "cooking", &row, &row).expect_err("name");
    assert!(err.message.contains("cooking"), "{}", err.message);
    let err = calibrate_pairwise_lock("python", "receta", &[], &row).expect_err("empty");
    assert!(err.message.contains("multiple"), "{}", err.message);
}

#[test]
fn assemble_emits_eleven_domain_locks_and_fifty_five_pairs() {
    let domains: Vec<(&str, Vec<f32>)> = CANONICAL_DOMAINS
        .iter()
        .enumerate()
        .map(|(index, name)| {
            let mut row = vec![0.0f32; DIM];
            row[index] = 1.0;
            (*name, row)
        })
        .collect();
    let borrowed: Vec<(&str, &[f32])> = domains
        .iter()
        .map(|(name, row)| (*name, row.as_slice()))
        .collect();
    let locks = assemble_canonical_locks(&borrowed).expect("registry");
    assert_eq!(locks.len(), 66);
    let mut ids: Vec<&str> = locks.iter().map(|lock| lock.domain_id.as_str()).collect();
    ids.sort();
    ids.dedup();
    assert_eq!(ids.len(), 66);
    assert!(ids.contains(&"python"));
    assert!(ids.contains(&"python_receta"));
    assert!(ids.contains(&"arquitectura_python"));
    assert!(!ids.contains(&"python_arquitectura"));
    let python = locks
        .iter()
        .find(|lock| lock.domain_id == "python")
        .unwrap();
    assert_eq!(python.quorum_k, 103);
    assert_eq!(python.noise_mask.active_count(), 1015);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn assembled_locks_roundtrip_through_lancedb() {
    let domains: Vec<(&str, Vec<f32>)> = CANONICAL_DOMAINS
        .iter()
        .enumerate()
        .map(|(index, name)| {
            let mut row = vec![0.0f32; DIM];
            row[index] = 1.0;
            row[(index + 40) % DIM] = -0.5;
            (*name, row)
        })
        .collect();
    let borrowed: Vec<(&str, &[f32])> = domains
        .iter()
        .map(|(name, row)| (*name, row.as_slice()))
        .collect();
    let catalog = assemble_canonical_catalog(&borrowed).expect("registry");
    let dir = std::env::temp_dir().join(format!("sf-pairs-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let uri = dir.to_str().unwrap();
    write_locks_with_manifests(uri, "domain_hypercubes", &catalog.locks, &catalog.manifests)
        .await
        .unwrap();
    let loaded = load_registry(uri).await.unwrap();
    assert_eq!(loaded.len(), 66);
    let pair_index = catalog
        .locks
        .iter()
        .position(|lock| lock.domain_id == "python_receta")
        .expect("pair");
    let stored = loaded.get("python_receta").expect("pair row");
    let fresh = &catalog.locks[pair_index];
    assert_eq!(stored.quorum_k, fresh.quorum_k);
    assert_eq!(stored.top_k_len, fresh.top_k_len);
    assert_eq!(stored.noise_mask, fresh.noise_mask);
    assert_eq!(
        stored.centroid.data[0].to_bits(),
        fresh.centroid.data[0].to_bits()
    );
    assert_eq!(
        loaded.manifest("python_receta"),
        Some(catalog.manifests[pair_index])
    );
    assert_eq!(catalog.manifests[pair_index].doc_count, 2);
    assert_ne!(catalog.manifests[pair_index].sha256, [0u8; 32]);
    let _ = std::fs::remove_dir_all(&dir);
}
