#ifndef PRINTS_H
#define PRINTS_H

#define __STDC_WANT_LIB_EXT2__ 1  //Define you want TR 24731-2:2010 extensions
#include <math.h>
#include <stdio.h>
#include <assert.h>
#include <stdarg.h>
#include <stdbool.h>
//#include "/home/pmorvalho/cbmc/src/ansi-c/library/stdlib.c"
//#include "/home/pmorvalho/cbmc/src/ansi-c/library/string.c"
#include <stdlib.h>
#include <string.h>
//#include "/home/pmorvalho/cbmc/src/ansi-c/library/stdio.c"

// Reverses a string 'str' of length 'len' starting at 'begin'
void reverse(char* str, int len, int starting_point);
 
// Converts a given integer x to string str[].
// d is the number of digits required in the output.
// If d is more than the number of digits in x,
// then 0s are added at the beginning.
int itoa(int x, char str[], int d);
 
// Converts a floating-point/double number to a string.
int ftoa(float n, char* res, int afterpoint);

// prints one char
int printChar(char* str, int offset, char c);
// prints a string
int printChars(char* str, int offset, const char* format);
// prints an integer
int printInt(char* str, int offset, int i);
// prints a float
int printFloat(char* str, int offset, float f);

// functions that introduce nondeterministic values in CBMC
int nondet_int();
char nondet_char();
float nondet_float();
bool nondet_bool();


#endif
