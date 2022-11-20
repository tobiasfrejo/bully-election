# Leader election with the bully algorithm and a comparision to an improved version

## Requirements

The system is developed and tested with Python 3.11.

Running the unittests and the implementation itself does not require anything other than the standard Python library. 

To run the batch comparison script, you will need `numpy`, `pandas`, and `matplotlib`
```
pip install -r requirements.txt
```

## Run

```
usage: [standard/improved]_bully.py [-h] [-n NUM_NODES] (-s STARTERS [STARTERS ...] | -S NUM_STARTERS)
                         (-a ALIVE [ALIVE ...] | -A NUM_ALIVE) [-p BASE_PORT]

options:
  -h, --help            show this help message and exit
  -n NUM_NODES, --num_nodes NUM_NODES
  -s STARTERS [STARTERS ...], --starters STARTERS [STARTERS ...]
  -S NUM_STARTERS, --num-starters NUM_STARTERS
  -a ALIVE [ALIVE ...], --alive ALIVE [ALIVE ...]
  -A NUM_ALIVE, --num-alive NUM_ALIVE
  -p BASE_PORT, --base_port BASE_PORT
```

You have to specify the number of nodes with `-n/--num_nodes NUM_NODES`. 

### Random set of nodes

The easiest way to test the implementations, is to make them generate a random list of nodes to run. The following will create a system of 10 nodes, turn on 8 randomly and of those, select 2 to both start an election:

```
python [standard/improved]_bully.py -p 4000 -n 10 -A 8 -S 2
```

### Specific setup

You can also specify exactly which nodes to start, by using the lower case `-a` and `-s`:

```
python [standard/improved]_bully.py -p 4000 -n 10 -a 0 2 5 7 -s 2 5
```

Make sure that the starters (defined with `-s`) are also in the list of alive nodes (defined with `-a`), otherwise the script nodes will never end because no election will occur. 


### Tests

To run the tests, simply run

```
python unittest_[standard/improved].py
```

### Batch tests for comparison

To easily compare the two implementations, we have created `comparison.py`, that will run both implementations over a range of tests and recording the time taken and the message counts. The tests are specified in a `.json` file with a list of test conditions. Each test condition has a `num` that is the count of nodes in the system, `alive` is a list of live nodes, and `starters` is a list of live nodes that should also start an election. 

E.g. from `batch.json`
```json
[
    {
        "num": 10,
        "alive": [1, 2, 4, 6, 8, 9],
        "starters": [2, 6]
    },
    ...
]
```

Run the comparison with

```
python compare.py
```

optionally define a base port with `-p`


The script then creates the bar charts in `results.png`

![Result image](results.png)

and a table of the values in a $\LaTeX$ formatted table in `results.tex`.

| Test \# | Standard message count |  Standard run time |  Improved message count |  Improved run time |
|---------|------------------------|--------------------|-------------------------|--------------------|
|     0.0 |                   48.0 |           3.270842 |                    12.0 |           0.333627 |
|     1.0 |                   20.0 |           3.237889 |                    14.0 |           0.786188 |
|     2.0 |                  230.0 |           3.225924 |                    19.0 |           0.393842 |
|     3.0 |                   83.0 |          11.845351 |                    56.0 |           5.808922 |
|     4.0 |                  577.0 |          12.083634 |                    51.0 |           0.814261 |
|     5.0 |                12223.0 |          15.498350 |                    53.0 |           1.358271 |
|     6.0 |                15628.0 |          11.334842 |                    53.0 |           1.459121 |
|     7.0 |                71917.0 |          59.520888 |                   106.0 |           4.092000 |