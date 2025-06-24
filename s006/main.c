#include <stdio.h>
#include <stdlib.h>

typedef struct n {
    int d;
    struct n *p, *n;
} n;
n *h = 0; // null

void dump() {
    printf("\n--- dumping linked list---\n");
    n *x = h;
    while(x) {
        printf("[%d] (address: %p, previous:%p, next:%p\n", x->d, (void *)x, x->p, x->n);
        x = x->n;
    }
}


void link(int v) {
    n *x;
    n *z = malloc(sizeof(n));
    z->d = v;
    z->p = 0;
    z->n = 0;
    if(!h){
        h = z; // if no head yet, make one
        return;
    }
    x = h;
    while (x->n) x = x->n; // loop until at the end of list
    x->n = z; // interchange links
    z->p = x;


}

// deletes specific value
int del(int v) {
    n *x = h;
    while(x) {
        if(x->d==v) {
            if (x->p) 
                x->p->n = x->n;
            else 
                    h = x->n;
            if (x->n)
                x->n->p=x->p;
            free(x);                 
        }
        x = x->n;
    }
}
int main() {
    link(13);
    link(14);
    link(22);
    link(49);
    link(440);
    link(42);
    dump();
    del(14);
    del(440);
    dump();
}
