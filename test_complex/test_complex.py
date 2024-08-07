import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer
from cocotb.binary import BinaryRepresentation
from cocotb.runner import get_runner

import random
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

@cocotb.test()
async def complex_add_test(dut):
    for i in range(1000):

        A = complex(int(random.uniform(-32768, 32767)), int(random.uniform(-32768, 32767)))
        B = complex(int(random.uniform(-32768, 32767)), int(random.uniform(-32768, 32767)))

        a = complex_to_32bits(A)
        b = complex_to_32bits(B)

        dut.a.value = a
        dut.b.value = b
        dut.op.value = 0

        await Timer(1, units='ns')

        sum = complex_overflow(A + B)
        assert dut.c.value == complex_to_32bits(sum)


@cocotb.test()
async def complex_conjugate_test(dut):
    for i in range(1000):

        A = complex(int(random.uniform(-32768, 32767)), int(random.uniform(-32768, 32767)))

        a = complex_to_32bits(A)

        dut.a.value = a
        dut.op.value = 1

        await Timer(1, units='ns')

        assert dut.c.value == complex_to_32bits(A.conjugate())

def test_complex_runner():
    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "rtl" / "complex.sv"]

    runner = get_runner("icarus")
    runner.build(
        sources=sources,
        hdl_toplevel="complex",
        always=True,
        build_args=[],
    )
    runner.test(
        hdl_toplevel="complex", test_module="test_complex", test_args=[]
    )


if __name__ == "__main__":
    test_complex_runner()