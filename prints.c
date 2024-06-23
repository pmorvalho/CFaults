#include "prints.h"
/* ftoa implementation based on https://www.geeksforgeeks.org/convert-floating-point-number-string */

int INT_PADDING = 1;
int FLOAT_DEC_POINTS = 6;

// Reverses a string 'str' of length 'len'
void reverse(char* str, int len, int start_point)
{
    int i = start_point, j = len - 1, temp;
    while (i < j) {
        temp = str[i];
        str[i++] = str[j];
        str[j--] = temp;
    }
}
 
// Converts a given integer x to string str[].
// d is the number of digits required in the output.
// If d is more than the number of digits in x,
// then 0s are added at the beginning.
int itoa(int x, char str[], int d)
{
    int i = 0;
    int neg = x >= 0 ? 0 : 1;
    if (!x){
      str[i++] = '0';
    }
    if (neg){
     str[i++] = '-';
     x = -x;
    }
    while (x) {
        str[i++] = (x % 10) + '0';
        x = x / 10;
    }
 
    // If number of digits required is more, then
    // add 0s at the beginning
    while (i < d)
        str[i++] = '0';
 
    reverse(str, i, !neg ? 0 : 1); // if the number if negative we do not want to reverse the signal
    str[i] = '\0';
    return i++;
}
 
// Converts a floating-point/double number to a string.
int ftoa(float n, char* res, int afterpoint)
{
    // Extract integer part
    int neg = n >= 0 ? 0 : 1;
    //int neg = 0;
    if ( neg ) {
      n = -n;
      res[0] = '-';
      res++;
    }
    int ipart = (int)n;
    //printf("%d %f\n", ipart, n); 
    // Extract floating part
    float fpart = n - (float)ipart;
    //fpart = roundf(fpart * powf(10, afterpoint)) / powf(10, afterpoint);
    // convert integer part to string
    int i = itoa(ipart, res, 0);
 
    // check for display option after point
    if (afterpoint != 0) {
        res[i++] = '.'; // add dot
        // Get the value of fraction part upto given no.
        // of points after dot. The third parameter
        // is needed to handle cases like 233.007
	int j;
	for (j = 0; j < afterpoint; j++) {
	  fpart *= 10;
	  int digit = (int)fpart;
	  res[i++] = digit + '0';
	  fpart -= (float)digit;
	}
    }
    return neg ? i + 1 : i ;
}

int printChar(char* str, int offset, char c){
    str[offset] = c;
    offset+=sizeof(c);
    str[offset+1]='\0';    
    return offset;
}

int printChars(char* str, int offset, const char* format){
    strcpy(str+offset, format);
    offset+=strlen(format);
    str[offset+1]='\0';
    return offset;
}

int printInt(char* str, int offset, int i){
   offset += itoa(i, str+offset, INT_PADDING);
   str[offset+1]='\0';   
   return offset;
}

int printFloat(char* str, int offset, float f){
  offset += ftoa(f, str+offset, FLOAT_DEC_POINTS);
  str[offset+1]='\0';
  return offset;
}
