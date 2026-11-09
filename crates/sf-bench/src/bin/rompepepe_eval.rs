use std::fs;

use serde::Serialize;
use sf_bench::{assert_publication_bounds, evaluate_matrix, generate_corpus};

#[derive(Serialize)]
struct Report {
    seed: String,
    locks: usize,
    vectors: usize,
    cosine_leaks: usize,
    cosine_leak_rate: f64,
    mode_a_blocked: usize,
    mode_b_blocked: usize,
    mode_c_blocked: usize,
    mode_c_containment: f64,
}

fn main() {
    let corpus = generate_corpus();
    let matrix = evaluate_matrix(&corpus);
    assert_publication_bounds(&matrix);
    let report = Report {
        seed: format!("0x{FIXTURE:X}", FIXTURE = sf_bench::FIXTURE_SEED),
        locks: corpus.locks.len(),
        vectors: matrix.total,
        cosine_leaks: matrix.cosine_leaks,
        cosine_leak_rate: matrix.cosine_leak_rate,
        mode_a_blocked: matrix.mode_a_blocked,
        mode_b_blocked: matrix.mode_b_blocked,
        mode_c_blocked: matrix.mode_c_blocked,
        mode_c_containment: matrix.mode_c_blocked as f64 / matrix.total as f64,
    };
    fs::create_dir_all("reports").expect("create reports/");
    let path = "reports/rompepepe_v3_matrix.json";
    let scpb_path = "reports/scpb_220_matrix.json";
    let json = serde_json::to_string_pretty(&report).unwrap();
    fs::write(path, &json).expect("write report");
    fs::write(scpb_path, &json).expect("write scpb report");
    println!(
        "cosine_leak_rate={:.4} mode_c={}/{} wrote {path} and {scpb_path}",
        report.cosine_leak_rate, report.mode_c_blocked, report.vectors
    );
}
