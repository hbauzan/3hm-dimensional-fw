//! Lossless `.xlsx` / `.zip` / `.csv` / `.parquet` export of an `fhv1` envelope.

use std::io::{Cursor, Write};
use std::sync::Arc;

use lancedb::arrow::arrow_array::{
    ArrayRef, BooleanArray, Float64Array, RecordBatch, UInt16Array, UInt8Array,
};
use lancedb::arrow::arrow_schema::{DataType, Field, Schema};
use rust_xlsxwriter::{Workbook, Worksheet, XlsxError};
use sf_kernels::{is_fhv1_rogue_dimension, DIM};
use zip::write::SimpleFileOptions;
use zip::ZipWriter;

use crate::fhv1_calibration::{Fhv1CalibrationSample, Fhv1ProfileRecord, Fhv1StorageError};

pub const FHV1_XLSX_MAX_ROWS: usize = 10_000;

pub enum Fhv1XlsxPayload {
    Xlsx(Vec<u8>),
    Zip(Vec<u8>),
}

pub fn export_xlsx(
    profile: &Fhv1ProfileRecord,
    samples: &[Fhv1CalibrationSample],
    max_rows_per_xlsx: usize,
) -> Result<Fhv1XlsxPayload, Fhv1StorageError> {
    if max_rows_per_xlsx == 0 {
        return Err(Fhv1StorageError::new(
            "max_rows_per_xlsx must be greater than zero",
        ));
    }
    if samples.len() <= max_rows_per_xlsx {
        return Ok(Fhv1XlsxPayload::Xlsx(workbook_bytes(profile, samples)?));
    }
    let mut cursor = Cursor::new(Vec::new());
    {
        let mut zip = ZipWriter::new(&mut cursor);
        let options = SimpleFileOptions::default();
        for (index, chunk) in samples.chunks(max_rows_per_xlsx).enumerate() {
            let name = format!("part_{:03}.xlsx", index + 1);
            let bytes = workbook_bytes(profile, chunk)?;
            zip.start_file(name, options)
                .map_err(Fhv1StorageError::new)?;
            zip.write_all(&bytes).map_err(Fhv1StorageError::new)?;
        }
        zip.finish().map_err(Fhv1StorageError::new)?;
    }
    Ok(Fhv1XlsxPayload::Zip(cursor.into_inner()))
}

pub fn export_csv(profile: &Fhv1ProfileRecord) -> Vec<u8> {
    let mut csv =
        String::from("dim,is_rogue_dim,min,max,mean,span,variance,std_dev,movement_tier\n");
    for dim in 0..DIM {
        let min = profile.min_vector[dim].to_string();
        let max = profile.max_vector[dim].to_string();
        let mean = profile.mean_vector[dim].to_string();
        let span = profile.span_vector[dim].to_string();
        let variance = profile.variance_vector[dim].to_string();
        let std_dev = profile.std_dev_vector[dim].to_string();
        csv.push_str(&format!(
            "{dim},{},{min},{max},{mean},{span},{variance},{std_dev},{}\n",
            u8::from(is_fhv1_rogue_dimension(dim)),
            profile.movement_tier_codes[dim],
        ));
    }
    csv.into_bytes()
}

pub fn export_parquet(profile: &Fhv1ProfileRecord) -> Result<Vec<u8>, Fhv1StorageError> {
    let batch = envelope_batch(profile)?;
    let mut cursor = Cursor::new(Vec::new());
    let mut writer = parquet::arrow::ArrowWriter::try_new(&mut cursor, batch.schema(), None)
        .map_err(Fhv1StorageError::new)?;
    writer.write(&batch).map_err(Fhv1StorageError::new)?;
    writer.close().map_err(Fhv1StorageError::new)?;
    Ok(cursor.into_inner())
}

fn workbook_bytes(
    profile: &Fhv1ProfileRecord,
    samples: &[Fhv1CalibrationSample],
) -> Result<Vec<u8>, Fhv1StorageError> {
    let mut workbook = Workbook::new();
    {
        let sheet = workbook.add_worksheet();
        sheet.set_name("Summary_Envelope").map_err(xlsx_err)?;
        write_summary(sheet, profile)?;
    }
    {
        let sheet = workbook.add_worksheet();
        sheet.set_name("Raw_Samples_Matrix").map_err(xlsx_err)?;
        write_samples(sheet, samples)?;
    }
    workbook.save_to_buffer().map_err(xlsx_err)
}

fn write_summary(
    sheet: &mut Worksheet,
    profile: &Fhv1ProfileRecord,
) -> Result<(), Fhv1StorageError> {
    for (col, name) in [
        "dim",
        "is_rogue_dim",
        "min",
        "max",
        "mean",
        "span",
        "variance",
        "std_dev",
        "movement_tier",
    ]
    .into_iter()
    .enumerate()
    {
        sheet.write_string(0, col as u16, name).map_err(xlsx_err)?;
    }
    for dim in 0..DIM {
        let row = (dim + 1) as u32;
        sheet.write_number(row, 0, dim as f64).map_err(xlsx_err)?;
        sheet
            .write_number(row, 1, f64::from(u8::from(is_fhv1_rogue_dimension(dim))))
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 2, profile.min_vector[dim])
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 3, profile.max_vector[dim])
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 4, profile.mean_vector[dim])
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 5, profile.span_vector[dim])
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 6, profile.variance_vector[dim])
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 7, profile.std_dev_vector[dim])
            .map_err(xlsx_err)?;
        sheet
            .write_number(row, 8, f64::from(profile.movement_tier_codes[dim]))
            .map_err(xlsx_err)?;
    }
    Ok(())
}

fn write_samples(
    sheet: &mut Worksheet,
    samples: &[Fhv1CalibrationSample],
) -> Result<(), Fhv1StorageError> {
    sheet.write_string(0, 0, "sample_id").map_err(xlsx_err)?;
    sheet.write_string(0, 1, "policy_id").map_err(xlsx_err)?;
    sheet.write_string(0, 2, "strategy_tag").map_err(xlsx_err)?;
    sheet.write_string(0, 3, "source_ref").map_err(xlsx_err)?;
    sheet.write_string(0, 4, "raw_text").map_err(xlsx_err)?;
    for dim in 0..DIM {
        sheet
            .write_string(0, (5 + dim) as u16, format!("dim_{dim}"))
            .map_err(xlsx_err)?;
    }
    for (index, sample) in samples.iter().enumerate() {
        let row = (index + 1) as u32;
        sheet
            .write_string(row, 0, &sample.sample_id)
            .map_err(xlsx_err)?;
        sheet
            .write_string(row, 1, &sample.policy_id)
            .map_err(xlsx_err)?;
        sheet
            .write_string(row, 2, &sample.strategy_tag)
            .map_err(xlsx_err)?;
        sheet
            .write_string(row, 3, &sample.source_ref)
            .map_err(xlsx_err)?;
        sheet
            .write_string(row, 4, &sample.raw_text)
            .map_err(xlsx_err)?;
        for dim in 0..DIM {
            sheet
                .write_number(row, (5 + dim) as u16, sample.vector[dim])
                .map_err(xlsx_err)?;
        }
    }
    Ok(())
}

fn envelope_batch(profile: &Fhv1ProfileRecord) -> Result<RecordBatch, Fhv1StorageError> {
    let mut dim = Vec::with_capacity(DIM);
    let mut rogue = Vec::with_capacity(DIM);
    let mut min = Vec::with_capacity(DIM);
    let mut max = Vec::with_capacity(DIM);
    let mut mean = Vec::with_capacity(DIM);
    let mut span = Vec::with_capacity(DIM);
    let mut variance = Vec::with_capacity(DIM);
    let mut std_dev = Vec::with_capacity(DIM);
    let mut tier = Vec::with_capacity(DIM);
    for index in 0..DIM {
        dim.push(index as u16);
        rogue.push(is_fhv1_rogue_dimension(index));
        min.push(profile.min_vector[index]);
        max.push(profile.max_vector[index]);
        mean.push(profile.mean_vector[index]);
        span.push(profile.span_vector[index]);
        variance.push(profile.variance_vector[index]);
        std_dev.push(profile.std_dev_vector[index]);
        tier.push(profile.movement_tier_codes[index]);
    }
    let schema = Arc::new(Schema::new(vec![
        Field::new("dim", DataType::UInt16, false),
        Field::new("is_rogue_dim", DataType::Boolean, false),
        Field::new("min", DataType::Float64, false),
        Field::new("max", DataType::Float64, false),
        Field::new("mean", DataType::Float64, false),
        Field::new("span", DataType::Float64, false),
        Field::new("variance", DataType::Float64, false),
        Field::new("std_dev", DataType::Float64, false),
        Field::new("movement_tier", DataType::UInt8, false),
    ]));
    let columns: Vec<ArrayRef> = vec![
        Arc::new(UInt16Array::from(dim)),
        Arc::new(BooleanArray::from(rogue)),
        Arc::new(Float64Array::from(min)),
        Arc::new(Float64Array::from(max)),
        Arc::new(Float64Array::from(mean)),
        Arc::new(Float64Array::from(span)),
        Arc::new(Float64Array::from(variance)),
        Arc::new(Float64Array::from(std_dev)),
        Arc::new(UInt8Array::from(tier)),
    ];
    RecordBatch::try_new(schema, columns).map_err(Fhv1StorageError::new)
}

fn xlsx_err(err: XlsxError) -> Fhv1StorageError {
    Fhv1StorageError::new(err)
}
