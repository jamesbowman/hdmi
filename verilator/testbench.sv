module testbench(
   input wire clock
);
    reg clk_pixel_x10;
    wire clk_pixel = clock;
    reg [23:0] rgb = 24'h112233;
    wire [15:0] audio_sample_word [1:0];
    
    reg [31:0] d = 0;
    wire [31:0] dInc = d[31] ? (48000) : (48000 - 74250000);
    wire [31:0] dN = d + dInc;
    always @(posedge clock)
    begin
      d = dN;
    end
    wire clk_audio = ~d[31];

    reg [15:0] sampleL = 16'h1111, sampleR = 16'h2222;
    always @(posedge clk_audio) begin
      sampleL <= sampleL + 16'h0137;
      sampleR <= sampleR + 16'h9471;
    end
    assign audio_sample_word[0] = sampleL;
    assign audio_sample_word[1] = sampleR;

    /* verilator lint_off PINMISSING */
    hdmi #(
      .VIDEO_ID_CODE(4),
      .VIDEO_REFRESH_RATE(60),
      .AUDIO_RATE(48000),
    ) hdmi_(
    .clk_pixel_x10(clk_pixel_x10),
    .clk_pixel(clk_pixel),
    .clk_audio(clk_audio),
    .rgb(rgb),
    .audio_sample_word(audio_sample_word)
    );
    /* verilator lint_on PINMISSING */
endmodule
