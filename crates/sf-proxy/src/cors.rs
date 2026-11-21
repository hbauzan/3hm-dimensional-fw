//! Browser origin allow-list. The daemon reads `SF_CORS_ORIGIN` once at startup.

use axum::http::{HeaderName, HeaderValue, Method};
use tower_http::cors::{AllowOrigin, Any, CorsLayer};

/// `Any` is the development fallback (`*`). `Origin` is one exact caller origin.
#[derive(Debug, Clone, PartialEq)]
pub enum CorsAllow {
    Any,
    Origin(HeaderValue),
}

impl CorsAllow {
    /// Empty, whitespace, and `*` allow any origin. Any other value must be one header token.
    pub fn parse(raw: Option<&str>) -> Result<Self, String> {
        match raw.map(str::trim).filter(|value| !value.is_empty()) {
            None | Some("*") => Ok(Self::Any),
            Some(origin) => {
                let value = HeaderValue::from_str(origin).map_err(|_| {
                    "SF_CORS_ORIGIN is not a valid Access-Control-Allow-Origin value".to_string()
                })?;
                Ok(Self::Origin(value))
            }
        }
    }

    pub fn layer(&self) -> CorsLayer {
        let layer = CorsLayer::new()
            .allow_methods([Method::GET, Method::POST, Method::OPTIONS])
            .allow_headers([
                axum::http::header::ACCEPT,
                axum::http::header::AUTHORIZATION,
                axum::http::header::CONTENT_TYPE,
                HeaderName::from_static("x-ddi-mode"),
                HeaderName::from_static("x-semantic-domain"),
                HeaderName::from_static("x-sf-wildcard-mode"),
            ])
            .expose_headers([
                HeaderName::from_static("x-sf-clauses-evaluated"),
                HeaderName::from_static("x-sf-decision"),
                HeaderName::from_static("x-sf-latency-ns"),
                HeaderName::from_static("x-sf-telemetry"),
                HeaderName::from_static("content-disposition"),
                HeaderName::from_static("x-sf-trace-id"),
                HeaderName::from_static("x-sf-fhv1-decision"),
            ]);
        match self {
            Self::Any => layer.allow_origin(Any),
            Self::Origin(value) => layer.allow_origin(AllowOrigin::exact(value.clone())),
        }
    }
}
