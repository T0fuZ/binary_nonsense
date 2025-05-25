/*
gcc bit_fields.c && a

Expanding thoughts on bit fields

Output:
Bit 0: 0Bit 1: 1
Bit 2: 0
Bit 3: 1
Bit 4: 0
Bit 5: 1
Bit 6: 0
Bit 7: 1
New value: 0x2B
0b00101011
0b00101011
0b00101011

 */


#include <stdio.h>
typedef union {
    unsigned char value;
    struct {
        unsigned char b0:1;
        unsigned char b1:1;
        unsigned char b2:1;
        unsigned char b3:1;
        unsigned char b4:1;
        unsigned char b5:1;
        unsigned char b6:1;
        unsigned char b7:1;
    } bits;
} Byte;

void print_binary_via_union(Byte b) {
    printf("0b");
    printf("%d", b.bits.b7);
    printf("%d", b.bits.b6);
    printf("%d", b.bits.b5);
    printf("%d", b.bits.b4);
    printf("%d", b.bits.b3);
    printf("%d", b.bits.b2);
    printf("%d", b.bits.b1);
    printf("%d", b.bits.b0);
    printf("\n");
}

void print_binary_mask(unsigned char val) {
    int i;
    printf("0b");
    for (i = 7; i >= 0; i--) {
        printf("%d", (val >> i) & 1);
    }
    printf("\n");
}

void print_binary_via_union2(Byte b) {
    printf("0b%d%d%d%d%d%d%d%d\n",
        b.bits.b7, b.bits.b6, b.bits.b5, b.bits.b4,
        b.bits.b3, b.bits.b2, b.bits.b1, b.bits.b0);
}

int main() {
    Byte b;
    b.value = 0b10101010;

    printf("Bit 0: %d", b.bits.b0);
    printf("Bit 1: %d\n", b.bits.b1);
    printf("Bit 2: %d\n", b.bits.b2);
    printf("Bit 3: %d\n", b.bits.b3);
    printf("Bit 4: %d\n", b.bits.b4);
    printf("Bit 5: %d\n", b.bits.b5);
    printf("Bit 6: %d\n", b.bits.b6);
    printf("Bit 7: %d\n", b.bits.b7);

    b.bits.b0 = 1;
    b.bits.b7 = 0;

    printf("New value: 0x%02X\n", b.value);
    print_binary_via_union(b);      // via union
    print_binary_via_union2(b);     // via union
    print_binary_mask(b.value);     // via mask value... hmm
    return 0;
}
