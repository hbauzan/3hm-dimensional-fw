//! TEI gRPC and HTTP embedders. Every gRPC request sets `normalize = true`.

use crate::embedder::BatchEmbedderClient;
use crate::normalize::{validate_and_normalize_f32_slice, validate_raw_f64_slice, NormalizeError};
use async_trait::async_trait;
use sf_kernels::{AlignedVec1024, DIM};

pub mod pb {
    tonic::include_proto!("tei.v1");
}

pub fn embed_request(input: &str) -> pb::EmbedRequest {
    pb::EmbedRequest {
        inputs: input.to_string(),
        truncate: false,
        normalize: Some(true),
        truncation_direction: pb::TruncationDirection::Right as i32,
        prompt_name: None,
        dimensions: None,
    }
}

pub struct TeiGrpcEmbedder {
    client: pb::embed_client::EmbedClient<tonic::transport::Channel>,
}

impl TeiGrpcEmbedder {
    pub async fn connect(url: impl AsRef<str>) -> Result<Self, String> {
        let client = pb::embed_client::EmbedClient::connect(url.as_ref().to_string())
            .await
            .map_err(|err| err.to_string())?;
        Ok(Self { client })
    }
}

#[async_trait]
impl BatchEmbedderClient for TeiGrpcEmbedder {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        let mut client = self.client.clone();
        let requests: Vec<_> = texts
            .iter()
            .map(|text| {
                let request = embed_request(text);
                if request.normalize != Some(true) {
                    return Err("fail-closed: EmbedRequest.normalize is not Some(true)".to_string());
                }
                Ok(request)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let response = client
            .embed_stream(tokio_stream::iter(requests))
            .await
            .map_err(|err| format!("fail-closed: TEI EmbedStream: {err}"))?;
        let mut inbound = response.into_inner();
        let mut vectors = Vec::with_capacity(texts.len());
        while let Some(message) = inbound
            .message()
            .await
            .map_err(|err| format!("fail-closed: TEI stream: {err}"))?
        {
            vectors.push(normalize_or_string(&message.embeddings)?);
        }
        if vectors.len() != texts.len() {
            return Err("fail-closed: TEI returned a mismatched embedding count".to_string());
        }
        Ok(vectors)
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        grpc_raw_f64_preflight(normalize)?;
        let widened = self.embed_batch_f32(texts).await?;
        Ok(widened.iter().map(widen_aligned_f32).collect())
    }
}

pub(crate) fn grpc_raw_f64_preflight(normalize: bool) -> Result<(), String> {
    if normalize {
        Ok(())
    } else {
        Err(
            "fail-closed: TeiGrpcEmbedder rejects unnormalized raw float64; use TeiHttpEmbedder"
                .to_string(),
        )
    }
}

pub(crate) fn widen_aligned_f32(vector: &AlignedVec1024) -> [f64; DIM] {
    vector.data.map(f64::from)
}

pub struct TeiHttpEmbedder {
    client: reqwest::Client,
    base_url: String,
}

impl TeiHttpEmbedder {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            client: reqwest::Client::new(),
            base_url: base_url.into(),
        }
    }
}

#[async_trait]
impl BatchEmbedderClient for TeiHttpEmbedder {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        let rows = self.post_embed(texts, true).await?;
        let mut vectors = Vec::with_capacity(rows.len());
        for row in rows {
            let nums = row
                .as_array()
                .ok_or_else(|| "fail-closed: TEI HTTP row is not an array".to_string())?;
            let mut raw = Vec::with_capacity(nums.len());
            for number in nums {
                let value = number.as_f64().ok_or_else(|| {
                    "fail-closed: TEI HTTP coordinate is not a number".to_string()
                })?;
                raw.push(value as f32);
            }
            vectors.push(normalize_or_string(&raw)?);
        }
        Ok(vectors)
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        let rows = self.post_embed(texts, normalize).await?;
        if rows.len() != texts.len() {
            return Err("fail-closed: TEI HTTP returned a mismatched embedding count".to_string());
        }
        let mut vectors = Vec::with_capacity(rows.len());
        for row in rows {
            let nums = row
                .as_array()
                .ok_or_else(|| "fail-closed: TEI HTTP row is not an array".to_string())?;
            let mut raw = Vec::with_capacity(nums.len());
            for number in nums {
                let value = number.as_f64().ok_or_else(|| {
                    "fail-closed: TEI HTTP coordinate is not a number".to_string()
                })?;
                raw.push(value);
            }
            vectors.push(
                validate_raw_f64_slice(&raw)
                    .map_err(|err: NormalizeError| format!("fail-closed: {err}"))?,
            );
        }
        Ok(vectors)
    }
}

impl TeiHttpEmbedder {
    async fn post_embed(
        &self,
        texts: &[&str],
        normalize: bool,
    ) -> Result<Vec<serde_json::Value>, String> {
        let url = format!("{}/embed", self.base_url.trim_end_matches('/'));
        let response = self
            .client
            .post(url)
            .json(&serde_json::json!({
                "inputs": texts,
                "normalize": normalize
            }))
            .send()
            .await
            .map_err(|err| format!("fail-closed: TEI HTTP /embed: {err}"))?;
        if !response.status().is_success() {
            return Err(format!(
                "fail-closed: TEI HTTP status {}",
                response.status()
            ));
        }
        let payload: serde_json::Value = response
            .json()
            .await
            .map_err(|err| format!("fail-closed: TEI HTTP body: {err}"))?;
        payload
            .as_array()
            .cloned()
            .or_else(|| {
                payload
                    .get("embeddings")
                    .and_then(|value| value.as_array())
                    .cloned()
            })
            .ok_or_else(|| "fail-closed: TEI HTTP payload is not an embedding list".to_string())
    }
}

fn normalize_or_string(values: &[f32]) -> Result<AlignedVec1024, String> {
    validate_and_normalize_f32_slice(values).map_err(|err: NormalizeError| err.to_string())
}

#[cfg(test)]
mod tests {
    use super::{grpc_raw_f64_preflight, widen_aligned_f32, TeiHttpEmbedder};
    use crate::embedder::BatchEmbedderClient;
    use sf_kernels::{AlignedVec1024, DIM};
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;

    #[test]
    fn grpc_raw_f64_rejects_unnormalized_and_widens_without_rounding() {
        let err = grpc_raw_f64_preflight(false).expect_err("normalize false");
        assert!(err.contains("fail-closed"));
        assert!(grpc_raw_f64_preflight(true).is_ok());
        let mut vector = AlignedVec1024::zeros();
        vector.data[0] = 0.1;
        let widened = widen_aligned_f32(&vector);
        assert_eq!(widened[0].to_bits(), f64::from(0.1f32).to_bits());
        assert_ne!(widened[0].to_bits(), 0.1f64.to_bits());
        assert_eq!(widened[1].to_bits(), 0.0f64.to_bits());
        assert_eq!(widened.len(), DIM);
    }

    #[tokio::test]
    async fn http_raw_f64_preserves_server_bits_for_both_normalize_flags() {
        let marker = 0.1f64;
        for normalize in [false, true] {
            let body = serde_json::to_string(&vec![vec![marker; DIM]]).expect("json");
            let request = serve_once(body).await;
            let embedder = TeiHttpEmbedder::new(format!("http://{}", request.addr));
            let rows = embedder
                .embed_batch_raw_f64(&["clause"], normalize)
                .await
                .expect("raw batch");
            assert_eq!(rows.len(), 1);
            assert_eq!(rows[0][0].to_bits(), marker.to_bits());
            assert_eq!(rows[0][DIM - 1].to_bits(), marker.to_bits());
            assert_ne!(rows[0][0].to_bits(), f64::from(marker as f32).to_bits());
            let captured = request.body.await.expect("request");
            let needle = if normalize {
                "\"normalize\":true"
            } else {
                "\"normalize\":false"
            };
            assert!(captured.contains(needle), "{captured}");
            assert!(captured.contains("\"inputs\":[\"clause\"]"), "{captured}");
        }
    }

    #[tokio::test]
    async fn http_raw_f64_rejects_a_short_row() {
        let body = serde_json::to_string(&vec![vec![1.0, 2.0]]).expect("json");
        let request = serve_once(body).await;
        let embedder = TeiHttpEmbedder::new(format!("http://{}", request.addr));
        let err = embedder
            .embed_batch_raw_f64(&["clause"], false)
            .await
            .expect_err("short");
        assert!(err.contains("fail-closed"), "{err}");
        let _ = request.body.await;
    }

    struct PendingRequest {
        addr: std::net::SocketAddr,
        body: tokio::task::JoinHandle<String>,
    }

    async fn serve_once(body: String) -> PendingRequest {
        let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
        let addr = listener.local_addr().expect("addr");
        let task = tokio::spawn(async move {
            let (mut socket, _) = listener.accept().await.expect("accept");
            let mut buf = Vec::new();
            let mut tmp = [0u8; 4096];
            loop {
                let n = socket.read(&mut tmp).await.expect("read");
                if n == 0 {
                    break;
                }
                buf.extend_from_slice(&tmp[..n]);
                if let Some(header_end) = find_subsequence(&buf, b"\r\n\r\n") {
                    let header = String::from_utf8_lossy(&buf[..header_end]);
                    let length = header_content_length(&header);
                    if buf.len() >= header_end + 4 + length {
                        break;
                    }
                }
            }
            let length = body.len();
            let response = format!(
                "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {length}\r\nconnection: close\r\n\r\n{body}"
            );
            socket.write_all(response.as_bytes()).await.expect("write");
            String::from_utf8_lossy(&buf).into_owned()
        });
        PendingRequest { addr, body: task }
    }

    fn find_subsequence(haystack: &[u8], needle: &[u8]) -> Option<usize> {
        haystack
            .windows(needle.len())
            .position(|window| window == needle)
    }

    fn header_content_length(header: &str) -> usize {
        header
            .lines()
            .find_map(|line| {
                let (name, value) = line.split_once(':')?;
                if name.eq_ignore_ascii_case("content-length") {
                    value.trim().parse().ok()
                } else {
                    None
                }
            })
            .unwrap_or(0)
    }
}
