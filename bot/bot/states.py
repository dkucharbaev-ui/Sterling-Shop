from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    entering_quantity = State()
    entering_recipient = State()
    choosing_payment = State()
    confirming = State()
