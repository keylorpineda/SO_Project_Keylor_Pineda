import time
import sys
sys.path.append('.')
from client import cliente_lib

print("Starting tests...")

# Test 1: Global State should be readable
print("Test 1: Read Global State...")
res = cliente_lib.global_state()
assert res["ok"]
initial_vendidos = res["state"]["0"]["vendidos"]
initial_reservados = res["state"]["0"]["reservados"]
print(f"Initial state in Zone 0: Sold={initial_vendidos}, Reserved={initial_reservados}")

# Test 2: Reserve a seat
print("Test 2: Reserve an available seat...")
res_matrix = cliente_lib.check(0)
assert res_matrix["ok"]
seat_r, seat_c = -1, -1
for r, row in enumerate(res_matrix["state"]):
    for c, state in enumerate(row):
        if state == "D":
            seat_r, seat_c = r, c
            break
    if seat_r != -1: break

assert seat_r != -1, "No available seats found for testing!"

res = cliente_lib.reserve(0, seat_r, seat_c)
assert res["ok"], f"Failed to reserve seat {seat_r}-{seat_c}"
tx_id = res["tx_id"]
print(f"Reserved seat {seat_r}-{seat_c} with TX: {tx_id}")

# Test 3: Confirm purchase
print("Test 3: Confirm purchase...")
res = cliente_lib.confirm(tx_id)
assert res["ok"]
print("Purchase confirmed!")

# Verify it's sold
res = cliente_lib.global_state()
assert res["state"]["0"]["vendidos"] == initial_vendidos + 1
print("State updated: 1 seat sold.")

# Test 4: Cancel an unconfirmed reservation
print("Test 4: Cancel an unconfirmed reservation...")
res2 = cliente_lib.reserve(0, seat_r, seat_c + 1 if seat_c + 1 < len(res_matrix["state"][0]) else 0)
assert res2["ok"]
tx_id2 = res2["tx_id"]
res_cancel = cliente_lib.cancel(tx_id2)
assert res_cancel["ok"]
print("Unconfirmed reservation cancelled!")

# Verify the first seat is still sold and the second is available
res = cliente_lib.global_state()
assert res["state"]["0"]["vendidos"] == initial_vendidos + 1
print("State updated: seat returned to available.")

print("All tests passed!")
