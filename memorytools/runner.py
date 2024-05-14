import time
from typing_extensions import Annotated
import typer

import memorytools.memorymonitor as memorymonitor
import memorytools.memoryanalysis as memoryanalysis

app = typer.Typer()


@app.command()
def snapshot(
        data_file: Annotated[str,
                    typer.Option(help="Path to the data file for persistence across instances")
                    ]= None):
    """
    Take a memory snapshot and exit. A data file can be provided to persist data across
    instances and be loaded in later.
    
    Args:
        data_file: Path to the data file for persistence across instances
    """
    mem_snap =memorymonitor.MemorySnapper(existing_data_file=data_file)
    mem_snap.take_memory_snapshot()
    mem_snap.close()
    print('Memory snapshot taken successfully.')

@app.command()
def export(
        data_file: Annotated[str, 
                             typer.Option(help="Path to the data file for persistence across instances")
                             ] = None,
        output_file: Annotated[str,
                               typer.Option(help="Path to the output file for exporting data")
                               ] = "memorymonitor_out.csv"):
    """
    Export memory data to a CSV file]
    
    Args:
        data_file: Path to the data file for persistence across instances
        output_file: Path to the output file for exporting data
    """
    mem_snap = memorymonitor.MemorySnapper(existing_data_file=data_file)
    mem_snap.export_to_csv(output_file)
    print(f'Data exported to {output_file} successfully.')


@app.command()
def monitor(interval: Annotated[float,
                                typer.Option(help="Time interval for monitoring in seconds")]= 1.0,
            data_file: Annotated[str, 
                                 typer.Option(help="Path to the data file for persistence across instances")
                                 ]= None):
    """
    Start monitoring memory usage in the background, this can be stopped by pressing Ctrl+C in the 
    terminal
    
    Args:
        interval: Time interval for monitoring in seconds
        data_file: Path to the data file for persistence across instances
    """
    mem_monitor = memorymonitor.MemoryMonitor(data_file=data_file, time_interval=interval)
    mem_monitor.start_monitoring()
    print('Memory monitoring started. Press Ctrl+C to stop.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if mem_monitor.is_monitoring():
            mem_monitor.stop_monitoring()
        print('Memory monitoring stopped.')

if __name__ == "__main__":
    app()