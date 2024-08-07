// a and b are complex numbers, each 16 bits for real and imaginary parts
// [31:16] is the real part, [15:0] is the imaginary part, twos complement

// op==0: add complex number a and b
// op==1: complex conjugate of a
`timescale 1ns/1ns

module complex(
    input op,
    input [31:0] a,
    input [31:0] b,
    output reg [31:0] c
);

    always_comb begin
        if (op == 0) begin
            c[31:16] = a[31:16] + b[31:16];
            c[15:0] = a[15:0] + b[15:0];
        end else begin
            c = { a[31:16], -a[15:0] };
        end
    end

endmodule