//! Arrow schema for one domain hypercube row.
//! Types are named through `lancedb::arrow` so the crate graph stays on LanceDB's Arrow 58.

use lancedb::arrow::arrow_schema::{DataType, Field, Schema};
use sf_kernels::{DEFAULT_QUORUM_K, DIM};
use std::sync::Arc;

pub const TABLE_NAME: &str = "domain_hypercubes";

pub fn domain_hypercube_arrow_schema() -> Arc<Schema> {
    let f32_item = Arc::new(Field::new("item", DataType::Float32, false));
    let u16_item = Arc::new(Field::new("item", DataType::UInt16, false));
    Arc::new(Schema::new(vec![
        Field::new("domain_id", DataType::Utf8, false),
        Field::new("version", DataType::UInt64, false),
        Field::new("polarity", DataType::UInt8, false),
        Field::new("l1_cosine_threshold", DataType::Float32, false),
        Field::new("l2_clause_threshold", DataType::Float32, false),
        Field::new("epsilon", DataType::Float32, false),
        Field::new("quorum_k", DataType::UInt16, false),
        Field::new(
            "centroid_vector",
            DataType::FixedSizeList(Arc::clone(&f32_item), DIM as i32),
            false,
        ),
        Field::new(
            "lo_vector",
            DataType::FixedSizeList(Arc::clone(&f32_item), DIM as i32),
            false,
        ),
        Field::new(
            "hi_vector",
            DataType::FixedSizeList(f32_item, DIM as i32),
            false,
        ),
        Field::new(
            "top_k_indices",
            DataType::FixedSizeList(u16_item, i32::from(DEFAULT_QUORUM_K)),
            false,
        ),
        Field::new("top_k_len", DataType::UInt16, false),
        Field::new("noise_mask", DataType::FixedSizeBinary(128), false),
        Field::new("corpus_doc_count", DataType::UInt64, false),
        Field::new("sha256_manifest", DataType::FixedSizeBinary(32), false),
    ]))
}
