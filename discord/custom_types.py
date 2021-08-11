class ReactionPaymentResult:
    success = False
    report = None

class CompletedTransaction:
    success = False
    report : str = None
    timestamp = None
    amount : int = 0
    payer : str = None
    recip : str = None
    # cause?