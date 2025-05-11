import json
import os
import sys
from rich.console import Console
from rich.progress import Progress

# Setup rich console for nice output
console = Console()

def load_jobs():
    """Load all jobs from the JSON file."""
    try:
        with open('useme_jobs.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[bold red]Error loading jobs: {str(e)}[/bold red]")
        return []

def load_presentation(filename):
    """Load a presentation from a file."""
    try:
        with open(os.path.join('presentations', filename), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[bold red]Error loading presentation {filename}: {str(e)}[/bold red]")
        return None

def save_presentation(filename, data):
    """Save a presentation to a file."""
    try:
        with open(os.path.join('presentations', filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        console.print(f"[bold red]Error saving presentation {filename}: {str(e)}[/bold red]")
        return False

def update_presentations():
    """Update all presentations with avatar URLs from jobs."""
    jobs = load_jobs()
    if not jobs:
        console.print("[bold red]No jobs found![/bold red]")
        return
    
    console.print(f"[green]Loaded {len(jobs)} jobs[/green]")
    
    # Create a dictionary of jobs by job_id for faster lookup
    jobs_by_id = {job['job_id']: job for job in jobs}
    
    # Get all presentation files
    presentation_files = [f for f in os.listdir('presentations') if f.endswith('.json')]
    console.print(f"[green]Found {len(presentation_files)} presentation files[/green]")
    
    updated_count = 0
    skipped_count = 0
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Updating presentations...", total=len(presentation_files))
        
        for filename in presentation_files:
            presentation_data = load_presentation(filename)
            if not presentation_data:
                progress.update(task, advance=1)
                skipped_count += 1
                continue
            
            # Check if the presentation has a useme_id
            if 'useme_id' not in presentation_data:
                console.print(f"[yellow]Presentation {filename} has no useme_id, skipping[/yellow]")
                progress.update(task, advance=1)
                skipped_count += 1
                continue
            
            useme_id = str(presentation_data['useme_id'])
            
            # Find the corresponding job
            if useme_id not in jobs_by_id:
                console.print(f"[yellow]No job found for useme_id {useme_id} in {filename}, skipping[/yellow]")
                progress.update(task, advance=1)
                skipped_count += 1
                continue
            
            job = jobs_by_id[useme_id]
            
            # Check if the job has an avatar URL
            if not job.get('avatar_url_source') or job['avatar_url_source'] == "https://cdn.useme.com/1.20.4/images/avatar/empty-neutral.svg?v=1.20.4":
                console.print(f"[yellow]Job {useme_id} has no avatar, skipping {filename}[/yellow]")
                progress.update(task, advance=1)
                skipped_count += 1
                continue
            
            # Update the presentation with the avatar URL
            if 'hero' in presentation_data:
                presentation_data['hero']['clientLogoSrc'] = job['avatar_url_source']
                presentation_data['hero']['clientLogoAlt'] = f"Logo {job.get('username', 'Klienta')}"
                
                # Save the updated presentation
                if save_presentation(filename, presentation_data):
                    console.print(f"[green]Updated {filename} with avatar from job {useme_id}[/green]")
                    updated_count += 1
                else:
                    console.print(f"[red]Failed to save {filename}[/red]")
                    skipped_count += 1
            else:
                console.print(f"[yellow]Presentation {filename} has no hero section, skipping[/yellow]")
                skipped_count += 1
            
            progress.update(task, advance=1)
    
    console.print(f"[bold green]Done! Updated {updated_count} presentations, skipped {skipped_count}[/bold green]")

if __name__ == "__main__":
    console.print("[bold cyan]Starting avatar update for presentations...[/bold cyan]")
    update_presentations() 