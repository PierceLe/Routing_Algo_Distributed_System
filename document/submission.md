Submission

Submit your solution here.

As a reminder:

Your source code should implement the required routing protocol with dynamic command features. You may use any programming language of your choice. However, your solution must include a wrapper script named Routing.sh that acts as the single entry point. For example, if you use Python, your script might look like:
#!/bin/bash
python3 your_solution.py "$@"

In addition, include a README file that details your coding environment, package versions, and clear instructions on how to run your program. The README should also explain any additional guidelines you followed when implementing dynamic events and graph operations. Although the README is for reference only and is not part of the mark, failure to submit it will remove your option to challenge any test case failures.

Your program must be executed using the following command:
/Routing.sh <Node-ID> <Port-NO> <Node-Config-File> <RoutingDelay> <UpdateInterval>

Here, <Node-ID> is a unique identifier (for example, A, B, C, ...), <Port-NO> is the port on which your node listens (ports start at 6000 and increase sequentially), and <Node-Config-File> is a file that specifies your node's immediate neighbours. This file’s first line contains the number of neighbours, followed by one line per neighbour with three tokens: the neighbour's identifier, the cost (a non-negative floating-point number) and the neighbour’s listening port.

Remember, all work must be your own. Unauthorised use of external resources (including AI tools where disallowed) or failure to adhere to academic integrity guidelines will result in penalties. If you have any questions regarding these policies or the allowed libraries, please consult your unit coordinator.