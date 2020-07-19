#include <stdio.h>
#include "Vtestbench.h"
#include "verilated_vcd_c.h"

int main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);
    Vtestbench* testbench = new Vtestbench;
    int i;

    FILE *log = fopen("log", "w");
    for (i = 0; i < (1650 * 750) + 10000; i++) {
      testbench->clock = 1;
      testbench->eval();
      unsigned tmds0 = testbench->v__DOT__hdmi___DOT__tmds[0];
      unsigned tmds1 = testbench->v__DOT__hdmi___DOT__tmds[1];
      unsigned tmds2 = testbench->v__DOT__hdmi___DOT__tmds[2];

      testbench->clock = 0;
      testbench->eval();

      fprintf(log, "%08x\n", tmds0 | (tmds1 << 10) | (tmds2 << 20));
    }
    printf("Simulation ended after %d cycles\n", i);
    delete testbench;
    fclose(log);

    exit(0);
}
