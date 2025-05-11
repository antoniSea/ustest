# Auto Proposal Scheduler

This system automatically scrapes jobs and generates proposals every 5 minutes.

## How It Works

The `auto_proposal_scheduler.py` script uses the `schedule` library to run the proposal generation function at regular 5-minute intervals. The script:

1. Connects to the database to get eligible jobs
2. Filters jobs with a minimum relevance score of 6
3. Generates proposals for up to 5 jobs per run
4. Automatically posts proposals to Useme
5. Logs all activity to `auto_proposal_scheduler.log`

## Setup and Usage

### Requirements

- Python 3.7+
- All dependencies from the main project
- `schedule` library (install with `pip install schedule`)

### Starting the Scheduler

To start the scheduler in the background:

```bash
./run_auto_scheduler.sh
```

This will:
- Activate your virtual environment (if available)
- Start the scheduler in the background using `nohup`
- Create a `scheduler.pid` file with the process ID
- Redirect output to `auto_scheduler.out`

### Stopping the Scheduler

To stop the running scheduler:

```bash
./stop_scheduler.sh
```

This will:
- Find the process ID from `scheduler.pid`
- Send a termination signal to the process
- Force kill if necessary
- Remove the `scheduler.pid` file

### Monitoring

You can monitor the scheduler's activity in several ways:

1. Check the log file: `tail -f auto_proposal_scheduler.log`
2. View stdout/stderr output: `cat auto_scheduler.out`
3. To verify the process is running: `ps -p $(cat scheduler.pid) || echo "Not running"`

## Configuration

You can modify the following settings in `auto_proposal_scheduler.py`:

- **Schedule interval**: Change `schedule.every(5).minutes` to your preferred interval
- **Minimum relevance score**: Adjust `min_relevance=6` to be more or less selective
- **Proposals per run**: Change `limit=5` to process more or fewer jobs each cycle

## Troubleshooting

If the scheduler stops unexpectedly:

1. Check `auto_proposal_scheduler.log` for error messages
2. Verify database connectivity
3. Ensure the Useme authentication is still valid
4. Restart the scheduler with `./run_auto_scheduler.sh` 