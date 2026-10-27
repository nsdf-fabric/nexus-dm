# NSDF Dark Matter CLI

The `nsdf_dark_matter` CLI offers a pool of operations to access and download the R76 dark matter dataset. The CLI serves as a top level component to access data in a workflow which can
then be analyzed with the [NSDF Dark Matter Library](https://nsdf-fabric.github.io/nexus-dm/library/). Check the [CLI guide](https://nsdf-fabric.github.io/nexus-dm/cli/) for a step by step walkthrough.

## NSDF CLI Usage Example

### Listing remote files

```bash
nsdf-cli ls
```

### Downloading a dataset

```bash
nsdf-cli download 07180827_0000_F0001
```

### Download all series matching a prefix with the `--all` flag:

```bash
nsdf-cli download 07180808_1558 --all
```

### Download multiple series

```txt
07180808_1558_F0006
07180808_1558_F0007
07180808_1558_F0008
07180808_1558_F0009
```

```bash
nsdf-cli download -f download.txt
```

### Download into a specific output directory:

```bash
nsdf-cli download 07180827_0000_F0001 -o /path/to/output
```

### Configure global settings

```bash
# View current configuration
nsdf-cli config

# Set global output directory
nsdf-cli config --output-global /path/to/output

# Set global endpoint
nsdf-cli config --endpoint https://example.com

# Reset configuration to defaults
nsdf-cli config --reset
```

### Prune downloaded series

```bash
# Remove all downloaded series from the global output directory (with confirmation)
nsdf-cli prune

# Skip confirmation prompt
nsdf-cli prune --force
```
