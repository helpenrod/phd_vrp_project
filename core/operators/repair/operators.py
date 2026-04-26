def greedy_repair(chromosome, ga):
    """Delegates to the GA's insertion-based repair operator."""
    return ga._repair(chromosome)


greedy_repair.stage = "repair"
greedy_repair.name = "greedy_repair"
greedy_repair.requires = set()
greedy_repair.forbids = set()
greedy_repair.supports = {'capacity', 'time_window', 'pickup_delivery'}
greedy_repair.representation = "direct_route"
