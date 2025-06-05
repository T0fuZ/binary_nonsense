#include <stdio.h>
#include <stdlib.h>

void print_array(int arr[], int size) {
    int i;  /* Declare loop variable at beginning */
    printf("Array contents: ");
    for (i = 0; i < size; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

void print_array_via_pointer(int *ptr, int size) {
    int i;  /* Declare loop variable at beginning */
    printf("Array via pointer: ");
    for (i = 0; i < size; i++) {
        printf("%d ", *(ptr + i));
    }
    printf("\n");
}

int main() {
    /* All variable declarations at the beginning - C89/C90 style */
    int arr1[5] = {10, 20, 30, 40, 50};     /* Static array */
    int *arr2;                              /* Dynamic array pointer */
    int a, b, c;                            /* Individual variables */
    int *ptr_array[3];                      /* Array of pointers */
    int (*ptr_to_arr)[5];                   /* Pointer to array (entire array) */
    int *ptr_to_first;                      /* Regular pointer to first element */
    int *ptr_to_dynamic;                    /* Pointer to dynamic array */
    int *temp_ptr;                          /* For pointer arithmetic */
    int i;                                  /* Loop counter */
    
    /* Initialize variables after all declarations */
    arr2 = (int*)malloc(4 * sizeof(int));
    arr2[0] = 100;
    arr2[1] = 200;
    arr2[2] = 300;
    arr2[3] = 400;
    
    a = 11;
    b = 22; 
    c = 33;
    ptr_array[0] = &a;
    ptr_array[1] = &b;
    ptr_array[2] = &c;
    
    ptr_to_arr = &arr1;
    ptr_to_first = arr1;
    ptr_to_dynamic = arr2;
    
    printf("=== DEBUGGING BREAKPOINT 1 ===\n");
    printf("Static array arr1 address: %p\n", (void*)arr1);
    printf("Dynamic array arr2 address: %p\n", (void*)arr2);
    printf("Pointer to array address: %p\n", (void*)ptr_to_arr);
    printf("Pointer to first element: %p\n", (void*)ptr_to_first);
    
    print_array(arr1, 5);
    print_array(arr2, 4);
    print_array_via_pointer(ptr_to_first, 5);
    
    printf("\n=== DEBUGGING BREAKPOINT 2 ===\n");
    printf("Array of pointers:\n");
    for (i = 0; i < 3; i++) {
        printf("ptr_array[%d] = %p, value = %d\n", i, (void*)ptr_array[i], *ptr_array[i]);
    }
    
    printf("\n=== DEBUGGING BREAKPOINT 3 ===\n");
    printf("Accessing via pointer to array:\n");
    for (i = 0; i < 5; i++) {
        printf("(*ptr_to_arr)[%d] = %d\n", i, (*ptr_to_arr)[i]);
    }
    
    printf("\n=== DEBUGGING BREAKPOINT 4 ===\n");
    printf("Pointer arithmetic:\n");
    temp_ptr = arr1;
    for (i = 0; i < 5; i++) {
        printf("Address: %p, Value: %d\n", (void*)temp_ptr, *temp_ptr);
        temp_ptr++;
    }
    
    // Modify some values for debugging
    arr1[2] = 999;
    arr2[1] = 888;
    
    printf("\n=== DEBUGGING BREAKPOINT 5 ===\n");
    printf("After modifications:\n");
    print_array(arr1, 5);
    print_array(arr2, 4);
    
    free(arr2);
    return 0;
}
