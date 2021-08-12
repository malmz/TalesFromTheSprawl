class ReactionPaymentResult:
    success = False
    report = None

class Transaction:
    success = False
    report : str = None
    timestamp = None # TODO
    amount : int = 0
    payer : str = None
    recip : str = None
    last_in_sequence : bool = True
    # cause?