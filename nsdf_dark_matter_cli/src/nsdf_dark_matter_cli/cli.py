from concurrent.futures import ThreadPoolExecutor, as_completed
import typer
from typing_extensions import Annotated
from typing import Optional
import os
import csv
import shutil
from importlib import resources
from importlib.metadata import version as semver
from rich import print as richprint
from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, TextColumn
from .download import download_routine, isvalid_midfile, expand_prefix
from .config import load_config, get_output_dir, set_output_dir, get_endpoint, set_endpoint, reset_config


app = typer.Typer(no_args_is_help=True, help="NSDF Dark Matter CLI")
console = Console()
progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}"),
    BarColumn(),
    DownloadColumn(),
    TransferSpeedColumn(),
    TimeRemainingColumn(),
)


def load_dataset():
    """
    Load Available Dataset
    """
    try:
        dataset = []
        with resources.files("nsdf_dark_matter_cli").joinpath("r_dataset.csv").open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dataset.append([row["filename"], row["size"], row["rseries"]])
    except Exception as e:
        richprint(f"[bold red]Failed to load dataset: {e}[/bold red]")
        raise typer.Exit(code=1)

    return dataset


DATASET = load_dataset()


@app.callback()
def main():
    """
    Load the global configuration at the start of every session
    """
    load_config()


@app.command()
def version():
    """
    CLI Version
    """
    richprint(f"NSDF Dark Matter CLI: {semver('nsdf_dark_matter_cli')}")


@app.command()
def ls(prefix: Annotated[str, typer.Option("--prefix","-p",help="List all files that start with prefix")] = "",
       limit: Annotated[int, typer.Option("--limit","-l",help="The number of files to show")] = None):
    """
    List all available files
    """

    is_match = (lambda f: f.startswith(prefix)) if prefix else (lambda _: True)
    limit = (1_000_000 if prefix else 10) if (limit is None or limit < 0) else limit

    for entry in DATASET:
        if limit <= 0:
            break

        filename, size, rseries = entry
        if is_match(filename):
            richprint(f"[bold green]{filename}\t{size}\t{rseries}[/bold green]")
            limit -= 1

    richprint(f"[bold blue]Total Files Available: {len(DATASET)}[/bold blue]")


@app.command()
def download(
    filename: Annotated[ str, typer.Argument( help="The name of the file to download, i.e, 07180808_1558_F0001"), ] = "",
    filelist: Annotated[str, typer.Option("--file-list", "-f", help="A path to a text file listing the files to download")] = "",
    all_series: Annotated[bool, typer.Option("--all", "-a", help="Download all the dumps of a series, i.e, 07180808_1558")] = False,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-o", show_default=False, help="Directory to download series files into (overrides the global config)")] = None
):
    """
    Download a Dataset
    """
    output_dir = output_dir or get_output_dir()
    files = set()
    errors = []
    # check if filelist flag is provided
    if filelist:
        if os.path.exists(filelist):
            with open(filelist, "r") as f:
                for line in f:
                    files.add(line.strip())
        else:
            errors.append(f"[bold red]path: {filelist} does not exists [/bold red]")
    elif all_series:
        prefix = filename.strip()
        if not prefix:
            richprint("[bold red]Must provide a prefix when using --all[/bold red]")
            raise typer.Exit(code=1)

        matches = expand_prefix(prefix, DATASET)
        if not matches:
            richprint(f"[bold red]No files found matching prefix {prefix}[/bold red]")
            raise typer.Exit(code=1)

        files.update(matches)
    else:
        files.add(filename.strip())

    if len(files) < 1:
        richprint("[bold red]Must provide at least 1 file[/bold red]")
        return

    with progress:
        with ThreadPoolExecutor(max_workers=min(len(files), 16)) as executor:
            futures = [executor.submit(download_routine, file, progress, output_dir) for file in files]

            for future in as_completed(futures):
                midfile, result = future.result()
                if isinstance(result, Exception):
                    errors.append(f"[bold red] {result} [/bold red]")

    if len(errors) > 0:
        for err in errors:
            richprint(err)
    else:
        richprint(f"[bold green]Successfully downloaded {len(files)} dataset(s)![/bold green]")


def dir_size(path):
    """
    Return the total size in bytes of all files under path
    """
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def format_size(num_bytes):
    """
    Format a byte count into a human readable string
    """
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024


@app.command()
def prune(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip the confirmation prompt")] = False,
):
    """
    Remove all downloaded series from the global output directory
    """
    output_dir = get_output_dir()
    if not os.path.isdir(output_dir):
        richprint(f"[bold yellow]No series found at {output_dir}[/bold yellow]")
        return

    series = [entry.name for entry in os.scandir(output_dir) if entry.is_dir() and isvalid_midfile(entry.name)]

    if not series:
        richprint(f"[bold yellow]No series found in {output_dir}[/bold yellow]")
        return

    if not force and not typer.confirm(f"Remove {len(series)} series from {output_dir}?"):
        richprint("[bold yellow]Aborted[/bold yellow]")
        raise typer.Exit(code=1)

    saved = 0
    for name in series:
        path = os.path.join(output_dir, name)
        saved += dir_size(path)
        shutil.rmtree(path, ignore_errors=True)

    richprint(f"[bold green]Removed {len(series)} series ({format_size(saved)} freed) from {output_dir}[/bold green]")


@app.command()
def config(
    output_global: Annotated[Optional[str], typer.Option("--output-global", show_default=False, help="Set the global output directory for downloads")] = None,
    endpoint: Annotated[Optional[str], typer.Option("--endpoint", show_default=False, help="Set the global download endpoint")] = None,
    reset: Annotated[bool, typer.Option("--reset", help="Reset the configuration to its defaults")] = False,
):
    """
    View or update the global CLI configuration
    """
    if reset:
        reset_config()
        richprint("[bold green]Configuration reset to defaults[/bold green]")

    if output_global:
        try:
            set_output_dir(output_global)
        except ValueError as e:
            richprint(f"[bold red]{e}[/bold red]")
            raise typer.Exit(code=1)
        richprint(f"[bold green]Global output directory set to {output_global}[/bold green]")

    if endpoint:
        try:
            set_endpoint(endpoint)
        except ValueError as e:
            richprint(f"[bold red]{e}[/bold red]")
            raise typer.Exit(code=1)
        richprint(f"[bold green]Global endpoint set to {endpoint}[/bold green]")

    if not reset and not output_global and not endpoint:
        richprint(f"[dark_turquoise]CLI Config[/dark_turquoise]")
        richprint(f"[dark_turquoise]Global output directory:[/dark_turquoise] [bright_white]{get_output_dir()}[/bright_white]")
        richprint(f"[dark_turquoise]Global endpoint:[/dark_turquoise] [bright_white]{get_endpoint()}[/bright_white]")
