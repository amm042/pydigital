int main(int argc, char** argv)
{
    // zero terminated list
    int alist[] = {2, 3, 5, 1, 9, 0};
    int *p = &alist[0];
    int sum = 0;
    while(*p){
        sum += *p++;
    }
    return sum;
}
