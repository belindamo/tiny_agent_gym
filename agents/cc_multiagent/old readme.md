we are making a generator critic agent pair using 2 instances of claude code

This is how it works given an initial `query`:
1. generator agent
    - given: initial query, git repo, generator's full prior trajectories, critic's last trajectory
    - generator agent can read/write to repo and also use git. 
    - the generator's trajectory is appended to a log file: <id>.txt. 
2. critic agent
    - given the generator's last trajectory, the critic's full prior trajectories, the git diff


if it hits 1m token for either, end. 

use claude code, see `reference_code/start_claude_task.py`. 

we want to make 2 pairs: one for executing an experiment given an experiment description and starting folder, a second for writing a paper based on the experiment itself. 
