use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Number of mining threads (defaults to number of CPU cores)
    pub threads: Option<usize>,

    /// Timeout for each challenge in minutes (defaults to 55)
    pub challenge_timeout_minutes: Option<u64>,

    /// Path to wallet configuration file
    pub wallet_config_path: String,

    /// Enable progress bar
    #[serde(default = "default_true")]
    pub show_progress: bool,

    /// Log level (trace, debug, info, warn, error)
    #[serde(default = "default_log_level")]
    pub log_level: String,
}

fn default_true() -> bool {
    true
}

fn default_log_level() -> String {
    "info".to_string()
}

impl Config {
    /// Load configuration from a TOML file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let contents =
            fs::read_to_string(path.as_ref()).context("Failed to read configuration file")?;

        let config: Config =
            toml::from_str(&contents).context("Failed to parse configuration file")?;

        Ok(config)
    }

    /// Create a default configuration
    pub fn default() -> Self {
        Self {
            threads: None,
            challenge_timeout_minutes: Some(55),
            wallet_config_path: "wallet.json".to_string(),
            show_progress: true,
            log_level: "info".to_string(),
        }
    }

    /// Save configuration to a TOML file
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let contents = toml::to_string_pretty(self).context("Failed to serialize configuration")?;

        fs::write(path.as_ref(), contents).context("Failed to write configuration file")?;

        Ok(())
    }

    /// Validate the configuration
    pub fn validate(&self) -> Result<()> {
        if let Some(timeout) = self.challenge_timeout_minutes {
            if timeout > 60 {
                anyhow::bail!("Challenge timeout should not exceed 60 minutes");
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.show_progress, true);
        assert_eq!(config.log_level, "info");
    }

    #[test]
    fn test_config_validation() {
        let mut config = Config::default();
        assert!(config.validate().is_ok());

        config.challenge_timeout_minutes = Some(70);
        assert!(config.validate().is_err());
    }
}
