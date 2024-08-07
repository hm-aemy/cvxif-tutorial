import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.clock import Clock
from cocotb.binary import BinaryRepresentation
from cocotb.runner import get_runner

from random import randint, getrandbits
from pathlib import Path


def complex_to_32bits(value):
    real = BinaryValue(int(value.real),n_bits=16,bigEndian=False,binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    imag = BinaryValue(int(value.imag),n_bits=16,bigEndian=False,binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    return BinaryValue(real.buff[::-1]+imag.buff[::-1])


def complex_overflow(value):
    real = value.real
    imag = value.imag
    if real < -32768:
        real += 65536
    if real > 32767:
        real -= 65536
    if imag < -32768:
        imag += 65536
    if imag > 32767:
        imag -= 65536
    return complex(real, imag)


def form_instruction(op):
    instr = BinaryValue(n_bits=32,bigEndian=False)
    instr[31:25] = 0
    instr[24:20] = 12
    instr[19:15] = 14
    instr[14:12] = op
    instr[11:7] = 14
    instr[6:0] = 0b1111011
    return instr

def reset_values(dut):
    dut.rst.value = 1
    dut.issue_valid.value = 0
    dut.issue_req_instr.value = 0
    dut.register_valid.value = 0
    dut.register_rs.value = [0, 0]
    dut.register_rs_valid.value = 0
    dut.result_ready.value = 0


async def start_clock(dut):
    c = Clock(dut.clk, 10, "ns")
    await cocotb.start(c.start())


async def wait_reset_cycle(dut):
    for i in range(3):
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0

def register_bitmask(num):
    return 0b01 | (0b10 if num > 1 else 0)

async def test_instruction(dut, instr, accepted, operands, result):
    # Test issue interface
    dut.issue_valid.value = 1
    dut.issue_req_instr.value = instr
    await RisingEdge(dut.clk) # clock edge ends cycle
    while dut.issue_ready.value == 0: # handshake?
        await RisingEdge(dut.clk) # no, maybe next cycle

    dut.issue_valid.value = 0 # only one instruction
    assert dut.issue_resp_accept.value == (1 if accepted else 0), f"Wrong acceptance for {instr}: {dut.issue_resp_accept.value}"
    if dut.issue_resp_accept.value == 0:
        return # not accepter, CPU aborts
    # Those are only valid with accepted
    assert dut.issue_resp_writeback.value == 1, f"Writeback not requested for {instr}"
    assert dut.issue_resp_register_read == register_bitmask(len(operands)), f"Wrong register read bitmask for {instr}: {dut.issue_resp_register_read}"

    await FallingEdge(dut.clk)

    # Test register interface
    dut.register_valid.value = 1
    dut.register_rs.value = [complex_to_32bits(operands[0]), complex_to_32bits(operands[1]) if len(operands) > 1 else 0]
    dut.register_rs_valid.value = register_bitmask(len(operands))
    await RisingEdge(dut.clk)
    while dut.register_ready.value == 0:
        await RisingEdge(dut.clk)
    dut.register_valid.value = 0

    await FallingEdge(dut.clk)

    # Test result interface
    # We add some backpresure here, we randomly accept the result or not
    # It must still work of course
    dut.result_ready.value = getrandbits(1)
    await RisingEdge(dut.clk)
    while dut.result_ready.value == 0 or dut.result_valid.value == 0:
        dut.result_ready.value = getrandbits(1)
        await RisingEdge(dut.clk)

    dut.result_ready.value = 0
    assert dut.result_data.value == complex_to_32bits(result), f"Wrong result for {instr}: {dut.result_data.value}"

    await FallingEdge(dut.clk)


@cocotb.test()
async def complex_add_test(dut):
    reset_values(dut)
    await start_clock(dut)
    await wait_reset_cycle(dut)

    A = 1 - 2j
    B = 3 + 4j

    await test_instruction(dut, 0xdeadbeef, False, [A, B], complex_overflow(A + B))
    await test_instruction(dut, form_instruction(0), True, [A, B], complex_overflow(A + B))

    for i in range(1000):
        A = complex(randint(-32768, 32767), randint(-32768, 32767))

        await test_instruction(dut, form_instruction(0), True, [A, B], complex_overflow(A + B))


@cocotb.test()
async def complex_conjugate_test(dut):
    reset_values(dut)
    await start_clock(dut)
    await wait_reset_cycle(dut)

    A = 1 - 2j

    await test_instruction(dut, 0xdeadbeef, False, [A], A.conjugate())
    await test_instruction(dut, form_instruction(1), True, [A], A.conjugate())

    for i in range(1000):
        A = complex(randint(-32768, 32767), randint(-32768, 32767))

        await test_instruction(dut, form_instruction(1), True, [A], A.conjugate())

def test_cvxif_runner():
    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "rtl" / "complex.sv", proj_path / "rtl" / "cvxif_complex.sv"]

    runner = get_runner("icarus")
    runner.build(
        sources=sources,
        hdl_toplevel="cvxif_complex",
        always=True,
        build_args=[],
    )
    runner.test(
        hdl_toplevel="cvxif_complex", test_module="test_cvxif", test_args=[]
    )


if __name__ == "__main__":
    test_cvxif_runner()