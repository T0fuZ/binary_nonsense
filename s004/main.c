#include <stdio.h>
/*
string array is just pointer
make:
gcc main.c && a

out:
random string
random string
ndom string
*/
int main() {
    char *p=NULL;
    char string[]="random string";
    p=string; // string is just array and pointer  so we dont need &

    
    printf("%s\n",string);
    printf("%s\n",p);
    
    
    
    p=(char *)&string[2];  // allowed, we can cast third element as new beginning of a string
    printf("%s\n",p);
}