All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- base/Dockerfile.centos7
- external/Dockerfile.centos7
- science/Dockerfile.centos7
- Makefile
- .gitlab-ci.yml

### Changed
- Updated and restructured project to allow for more streamlined builds
- Integrated changes for working with GitLab CI
- Updating the base working environment OS to CentOS7 (from CentOS 6)

## [1.3.2] - 2020-01-29
### Added
- CHANGELOG

### Changed
- Update version of espa_surface_reflectance_lasrc (2.0.1)
- Update version of espa_aq_refl (1.1.0)
- Update version fo espa-plotting (0.5.1)
- Rename occurrences of 'orca' to aquatic reflectance (aq_refl) as necessary
- Updated statistics and plotting interfacing to locate aquatic reflectance band products
- Removed references to previous orca band products (rrs and chlor_a)
- Landsat Level-1 metadata is only included in the product bundle if the order includes the level-1 source data, or if it was specifically requested

### Fixed
- Do not generate statistics for the Sentinel-2 Aerosol QA band
- Fix bug where unused .stats files are potentially delivered in the statistics archive

## [1.3.1] - 2019-12-06
### Changed
- Initial updates for ESPA 2.35.0 (internal-only release)
- Update version of espa_spectral_indices (2.9.0)
- Update version of espa_surface_temperature (2.5.0)
- Update version of espa_surface_temperature_rit (2.5.0)
- Update version of espa_product_formatter (1.19.0)
