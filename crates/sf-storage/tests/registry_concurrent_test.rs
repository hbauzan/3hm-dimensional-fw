use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

use sf_kernels::{AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DIM, MAX_TOPK};
use sf_storage::{
    load_validated_vec1024, DomainRegistry, HotRegistry, UNALIGNED_ARROW_BUFFER_LOADS,
};

fn lock_at(version: u64) -> DomainHypercubeLock {
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: "python".to_string(),
        centroid: AlignedVec1024::zeros(),
        lo: AlignedVec1024::zeros(),
        hi: AlignedVec1024 { data: [1.0; DIM] },
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: [0u16; MAX_TOPK],
        top_k_len: 1,
        quorum_k: 103,
        l1_cosine_threshold: 0.2,
        l2_clause_threshold: 0.2,
        polarity: 0,
        domain_version: version,
    })
}

fn registry(version: u64) -> Arc<DomainRegistry> {
    let lock = lock_at(version);
    Arc::new(DomainRegistry {
        locks_by_id: [(lock.domain_id.clone(), Arc::new(lock))]
            .into_iter()
            .collect(),
        all_locks: Vec::new(),
        manifests: std::collections::HashMap::new(),
    })
}

#[test]
fn thirty_two_readers_survive_hot_swap() {
    let hot = Arc::new(HotRegistry::new(registry(1)));
    let stop = Arc::new(AtomicBool::new(false));
    let started = Arc::new(AtomicUsize::new(0));
    let mut joins = Vec::new();
    for _ in 0..32 {
        let hot = Arc::clone(&hot);
        let stop = Arc::clone(&stop);
        let started = Arc::clone(&started);
        joins.push(thread::spawn(move || {
            started.fetch_add(1, Ordering::Relaxed);
            let mut loads = 0u64;
            while !stop.load(Ordering::Relaxed) {
                let snapshot = hot.load();
                let version = snapshot.get("python").unwrap().domain_version;
                assert!((1..=40).contains(&version));
                loads += 1;
            }
            loads
        }));
    }
    while started.load(Ordering::Relaxed) < 32 {
        thread::yield_now();
    }
    for version in 2..=40 {
        hot.store(registry(version));
    }
    thread::sleep(Duration::from_millis(20));
    stop.store(true, Ordering::Relaxed);
    for join in joins {
        let loads = join.join().expect("reader panicked");
        assert!(loads > 0);
    }
}

#[test]
fn unaligned_slice_increments_counter_and_rejects_nan() {
    let mut raw = vec![0.25f32; DIM + 32];
    let slice = unaligned_window(&raw);
    let before = UNALIGNED_ARROW_BUFFER_LOADS.load(Ordering::Relaxed);
    let loaded = load_validated_vec1024(slice).unwrap();
    assert_eq!(loaded.data[0].to_bits(), 0.25f32.to_bits());
    assert!(UNALIGNED_ARROW_BUFFER_LOADS.load(Ordering::Relaxed) > before);

    raw[0] = f32::NAN;
    let aligned = AlignedVec1024::from_slice(&raw[..DIM]).unwrap();
    // from_slice does not check finiteness; the Arrow loader does.
    let mut finite = aligned.data;
    finite[4] = f32::INFINITY;
    assert!(load_validated_vec1024(&finite).is_err());
}

fn unaligned_window(raw: &[f32]) -> &[f32] {
    for shift in 0..16 {
        let window = &raw[shift..shift + DIM];
        if !(window.as_ptr() as usize).is_multiple_of(64) {
            return window;
        }
    }
    panic!("failed to construct an unaligned f32 window");
}
