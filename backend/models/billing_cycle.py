from mongoengine import (
    DateTimeField,
    DecimalField,
    Document,
    StringField,
    ReferenceField,
)


class BillingCycle(Document):
    organization = ReferenceField("Organization", required=True)
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)
    base_amount = DecimalField(precision=2)
    usage_amount = DecimalField(precision=2)
    credits_applied = DecimalField(precision=2, default=0)
    final_amount = DecimalField(precision=2)
    status = StringField(choices=["draft", "finalized", "paid"])
    payment_date = DateTimeField()

    meta = {"indexes": [("organization", "start_date", "end_date"), "status"]}
