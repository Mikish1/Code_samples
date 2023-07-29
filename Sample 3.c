
#include "PartC.h"
#include <stdio.h>
#include <sys/mman.h>


 static void *space = NULL;         // To store the allocated space
 static header_t *head = NULL;      // Head of the list
 static header_t *ptr = NULL;       // Pointer to the current list location
 static void *end = NULL;           // Store the address of the end of the allocated space


int M_Init(int size) {
    int bytes;

    // Fail if M_Init was already used to allocate space.
    if (space != NULL){
        printf("space already initialized.\n");
        return -1;
    }
    // Fail if the requested amount of space is invalid.
    if (size <= 0){
        return -1;
    }
    // Round up to the nearest multiple of 16 bytes.
    for (int x = 16; x < size;){
        x = x*2;
        bytes = x;
    }

    space = mmap(NULL, bytes + sizeof(header_t), PROT_READ | PROT_WRITE, MAP_ANON | MAP_PRIVATE, -1, 0);

    // Return if space couldn't be allocated.
    if (!space){
        return -1;
    }
    //Initialize the head of the list.
    else {
        head = (void *)(space);
        head->size = bytes;
        head->magic = 321;
        head->next = NULL;
        ptr = head;
        end = (header_t *)head+bytes + sizeof(header_t);
        return 0;
    }
}


void *M_Alloc(int size){
    // Fail if invalid size.
    if (size <= 0){
        return NULL;
    }

     header_t *newHeader = NULL;
     int bytes;
     if (size < 16){
         bytes = 16;
     }
    // Round up to the nearest multiple of 16 bytes.
     for (int x = 16; x <= size;){
         x = x*2;
         bytes = x;
     }

     if (head->size < bytes){
         printf("Not enough space remaining.\n");
         return NULL;
     }

     header_t *current = ptr;
     // used to check if the list has been looped through for the next fit policy.
     int s = 0;
     while (current){

         // Return if not enough space was found in the list
         if (current == ptr && s == 1){
             printf("Not enough contiguous space.\n");
             return NULL;
         }

         // Stop if a satisfactory chunk is found.
         if (current->size >= bytes && current->magic != 123) {
             break;
         }
         // Start at the beginning of the list if past the end.
         else if ((header_t *)end <= current+current->size+bytes && current != head && current->next == NULL){
             current = head+1;
         }

         else current = current->next;
         s = 1;
     }
     // If at the head create a new header after.
     if (current == head){
         newHeader = (void *)(head+1);
         head->next = newHeader;
     }
     // Create the new header after the current pointer location.
     else if (current == NULL){
         newHeader = (void *)(ptr + ptr->size+sizeof(footer_t));
         ptr->next = newHeader;
         newHeader->next = NULL;
     }

     else
         newHeader = current;

     //update the info of the new header and create the new footer after the allocated space.
     newHeader->size = bytes;
     newHeader->magic = 123;
     footer_t *newFooter = (void *)(newHeader + newHeader->size);
     newFooter->size = bytes;
     newFooter->magic = 123;

     //Update the pointer to the new header and update the remaining space left in the list.
     ptr = newHeader;
     head->size = head->size-bytes-(int)sizeof(header_t)-(int)sizeof(footer_t);

     return (void *)(newHeader + 1);
}


int M_Free(void *p){
    // Return if not passed a valid pointer.
    if (!p){
        printf("invalid pointer\n");
        return -1;
    }
    header_t *header = (header_t*)(p-sizeof(header_t));             // Header of chunk being freed.
    footer_t *footer = (footer_t *) (header + header->size);        // Footer of chunk being freed.
    footer_t *pFooter = (footer_t*)(header - sizeof(footer_t));     // Footer of previous chunk if it exists
    header_t *next = NULL;                                          // Header of next chunk if it exists.

    // Check for the next chunk.
    if (header->next != NULL){
        next = (header_t*)(footer+sizeof(footer_t));
    }
    // Check for previous chunk.
    if ((header_t*)pFooter <= head){
        pFooter = NULL;
    }

    // If both the previous and next chunks are free
    if ((pFooter != NULL && pFooter->magic == 321) &&(next != NULL && next->magic == 321)){
        // Get the previous head and next footer and update their sizes.
        header_t *prevHead = (header_t*)(pFooter - pFooter->size);
        footer_t *nextFooter = (footer_t*)(next+next->size);
        prevHead->size = prevHead->size + header->size + (int)sizeof(header_t) + next->size + (int) sizeof(footer_t);
        nextFooter->size = prevHead->size;
        // Check if there's a chunk after.
        if (next->next != NULL){
            prevHead->next = next->next;
        }
        else {
            prevHead->next = NULL;
        }
        // Move ptr if it on the chunk being coalesced.
        if (ptr == header){
            ptr = prevHead;
        }
        if (ptr == next){
            ptr = prevHead;
        }
        // Update the head size and nullify the header and footer.
        head->size = head->size + header->size + (int)sizeof(header_t) + (int)sizeof(footer_t);
        header = NULL;
        footer = NULL;
    }
    // If the previous chunk is only free.
    else if (pFooter != NULL && pFooter->magic == 321){
        // Get the previous head, update its size, update the footers size.
        header_t *prevHead = (header_t*)(pFooter - pFooter->size);
        prevHead->size = prevHead->size + header->size + (int)sizeof(header_t);
        footer->size = prevHead->size + (int)sizeof(header_t);
        // Check if there's a chunk after.
        if (next != NULL){
            prevHead->next = next;
        }
        else {
            prevHead->next = NULL;
        }
        // Move ptr if it on the chunk being coalesced.
        if (ptr == header){
            ptr = prevHead;
        }
        // Update the head size and nullify the header, update the footer to be marked as free.
        head->size = head->size + header->size + (int)sizeof(header_t);
        header = NULL;
        footer->magic = 321;
    }
    // If the next chunk is only free.
    else if (next != NULL && next->magic == 321){
        // Get the next footer and update it's size, update the size of the header and new footer.
        footer_t *nextFooter = (footer_t*)(next+next->size);
        header->size = header->size + next->size + (int) sizeof(footer_t);
        nextFooter->size = header->size;
        header->next = next->next;

        // Move ptr if it on the chunk being coalesced.
        if (ptr == next){
            ptr = header;
        }
        // Update the head size and nullify the footer, update the footer to be marked as free.
        header->magic = 321;
        head->size = head->size + header->size + (int)sizeof(footer_t);
        footer = NULL;
    }

    // If it can't be coalesced mark the chunk as free and update the size of the header.
    else {
        footer->magic = 321;
        head->size = head->size + header->size;
        header->magic = 321;
    }
    return 0;
}


void M_Display(){
    header_t *current = head->next;
    // Display the address and size of current chunk if it is free.
    while (current){
        if (current->magic==321){
            printf("Address: %p\nSize: %d\n", current, current->size);
        }
        current = current->next;
    }
}
