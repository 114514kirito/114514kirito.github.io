---
title: xv6 riscv book chapter 5：Page faults
date: 2025-07-27
tag: 
- OS
- risc-v
category: 
- OS
- risc-v
---

# xv6 riscv book chapter 5：Page faults

The RISC-V CPU raises a page-fault exception when a virtual address is used that has no mapping in the page table, or has a mapping whose PTE_V flag is clear, or a mapping whose permission bits (PTE_R, PTE_W, PTE_X, PTE_U) forbid the operation being attempted. RISC-V distinguishes three kinds of page fault: load page faults (caused by load instructions), store page faults (caused by store instructions), and instruction page faults (caused by fetches of instructions to be executed). The scause register indicates the type of the page fault and the stval register contains the address that couldn’t be translated.

当使用的虚拟地址在页表中没有映射、或其映射的 PTE_V 标志位为清除状态、亦或其权限位（PTE_R、PTE_W、PTE_X、PTE_U）禁止当前尝试的操作时，RISC-V CPU 会触发缺页异常（page-fault exception）。RISC-V 将缺页异常分为三类：读缺页（由 load 指令引起）、写缺页（由 store 指令引起）以及指令缺页（由取指执行引起）。scause 寄存器指示了缺页异常的类型，而 stval 寄存器则包含了无法被转换的地址。

The combination of page tables and page faults is a powerful tool. Page tables give the kernel a level of indirection between virtual and physical addresses, so that the kernel can control the structure and content of address spaces. Page faults allow the kernel to intercept loads and stores and, by modifying the page table, specify on the fly what data those references refer to. The kernel can use these capabilities to increase efficiency: for example, copy-on-write fork allows the kernel to transparently share memory between parent and child, avoiding the cost of copying pages that neither write. Application programmers can also benefit. One possibility is memory-mapped files, where the kernel uses paging to cause a file’s content to appear in an application’s address space, transparently reading file blocks in response to page faults. Another is lazy memory allocation, which allows a program to ask for a huge virtual address space, but only to pay the cost of allocating physical memory for the pages the program actually reads and writes. xv6 uses page faults for only one purpose: lazy allocation.

页表与缺页异常的结合是一个强大的工具。页表为内核提供了虚拟地址与物理地址之间的间接层，使得内核可以控制地址空间的结构和内容。缺页异常允许内核拦截读写操作，并通过修改页表，动态地指定这些引用所指向的数据。内核可以利用这些能力来提高效率：例如，写时复制（copy-on-write）fork 允许内核在父子进程间透明地共享内存，从而避免复制那些双方都不会修改的页面的开销。应用程序员也能从中受益。一种可能性是内存映射文件（memory-mapped files），内核利用分页机制使文件内容出现在应用程序的地址空间中，通过响应缺页异常来透明地读取文件块。另一种是延迟内存分配（lazy memory allocation），它允许程序请求巨大的虚拟地址空间，但仅在程序实际读写页面时才支付分配物理内存的代价。xv6 仅将缺页异常用于一个目的：延迟分配。

Before proceeding, please read the functions sys_sbrk() in kernel/sysproc.c, and vmfault in kernel/vm.c.Search for calls to vmfault in kernel/trap.c and kernel/vm.c.

在继续之前，请阅读 kernel/sysproc.c 中的 sys_sbrk() 函数，以及 kernel/vm.c 中的 vmfault 函数。在 kernel/trap.c 和 kernel/vm.c 中查找对 vmfault 的调用。

## 5.1 Lazy allocation

xv6’s lazy allocation has two parts. First, when an application asks for memory by calling sbrk with the flag SBRK_LAZY, the kernel notes the increase in size, but does not allocate physical memory and does not create PTEs for the new range of virtual addresses. Second, on a page fault on one of those new addresses, the kernel allocates a page of physical memory and maps it into the page table. The kernel implements lazy allocation transparently to applications: no modifications to applications are necessary for them to benefit. Lazy allocation is convenient for applications because they don’t have to accurately predict how much memory they will need. For example, an application may process input, but not know in advance how large the input will be. With lazy allocations an application can ask for memory for the worst case, but not have to pay for this worst case: the kernel doesn’t have to do any work at all for pages that the application never uses.

xv6 的延迟分配由两部分组成。首先，当应用程序通过调用带有 `SBRK_LAZY` 标志的 `sbrk` 来请求内存时，内核仅记录大小的增加，但不分配物理内存，也不为新的虚拟地址范围创建页表项（PTE）。其次，当在这些新地址上发生缺页异常时，内核才分配一页物理内存并将其映射到页表中。内核实现的延迟分配对应用程序是透明的：无需进行任何修改。向应用程序提供这些功能是使其受益的必要条件。延迟分配对应用程序来说非常方便，因为它们不必准确预测自己需要多少内存。例如，一个应用程序可能会处理输入，但预先并不知道输入会有多大。通过延迟分配，应用程序可以按最坏情况申请内存，但不必为此付出代价：对于应用程序从未使用的页面，内核完全不需要做任何工作。

Furthermore, if the application is asking to grow the address space by a lot, then sbrk without lazy allocation is expensive: if an application asks for a gigabyte of memory, the kernel has to allocate and zero 262,144 4096-byte physical pages. Lazy allocation allows this cost to be spread over time. On the other hand, lazy allocation incurs the extra overhead of page faults, which involve a user/kernel transition. Operating systems can reduce this cost by allocating a batch of consecutive pages per page fault instead of one page and by specializing the kernel entry/exit code for such page-faults (though xv6 does neither).

此外，如果应用程序请求大幅增加地址空间，那么没有延迟分配的 sbrk 将非常昂贵：如果应用程序请求 1GB 内存，内核必须分配并清零 262,144 个 4096 字节的物理页。延迟分配允许将这一成本分摊到一段时间内。另一方面，延迟分配会产生缺页中断的额外开销，这涉及用户态与内核态的转换。操作系统可以通过在每次缺页中断时分配一批连续页面（而非单个页面），以及为这类缺页中断专门优化内核进入/退出代码来降低这一成本（尽管 xv6 这两点都没有做）。

On the other hand, when taking a page fault for a lazily-allocated page, the kernel may find that it has not free memory to allocate. In this case, the kernel has no easy way of returning an out-of-memory error to the application and instead kills the application. For applications that prefer an error on a failed allocation, xv6 allows an application to allocate memory eagerly by calling sbrk with the flag sbrk_EAGER.

另一方面，当为延迟分配的页面处理缺页中断时，内核可能会发现已经没有可分配的空闲内存了。在这种情况下，内核没有简便的方法向应用程序返回内存不足（out-of-memory）错误，而是直接杀死该进程。对于那些希望在分配失败时收到错误的应用程序，xv6 允许应用程序通过调用带有 sbrk_EAGER 标志的 sbrk 来进行立即分配。

## 5.2 Code

The system call sbrk ( n ) grows (or shrinks if n is negative) a process’s memory size by n bytes, and returns the start of the newly allocated region (i.e., the old size). The kernel implementation is sys_sbrk (3801).

系统调用 sbrk(n) 将进程的内存大小增加 n 字节（如果 n 为负数则减小），并返回新分配区域的起始地址（即旧的大小）。其内核实现是 sys_sbrk (3801)。

If the application specifies SBRK_EAGER, the system call is implemented by the function growproc (2353), growproc calls uvmalloc. uvmalloc (1628) allocates physical memory with kalloc, zeros the allocated memory, and adds PTEs to the user page table with mappages.

如果应用程序指定了 SBRK_EAGER，该系统调用将由 growproc (2353) 函数实现。growproc 调用 uvmalloc。uvmalloc (1628) 通过 kalloc 分配物理内存，将分配的内存清零，并使用 mappages 向用户页表添加页表项（PTE）。

If the applications allocates memory lazily, sys_sbrk just increments the process’s size (myproc ( ) ->sz) by n and returns the old size; it does not allocate physical memory or add PTEs to the process’s page table.

如果应用程序采用延迟分配（lazily）内存，sys_sbrk 仅将进程的大小（myproc ( ) ->sz）增加 n 并返回旧的大小；它不会分配物理内存，也不会向进程页表添加 PTE。

When a process loads or stores to a virtual address that lacks a valid page-table mapping, the CPU will raise page-fault exception. usertrap checks for this case (3372) and calls vmfault (1879) to handle the page fault. vmfault checks that the faulting address is within the region previously granted by sbrk, allocates a page of physical memory with kalloc, zeros the allocated page, and adds a PTE to the user page table with mappages. Xv6 sets the PTE_W, PTE_R, PTE_U, and PTE_V flags in the PTE for the new page. Then, usertrap resumes the process at the instruction that caused the fault. Because the PTE is now valid, the re-executed load or store instruction will execute without a fault.

当进程对缺乏有效页表映射的虚拟地址进行加载（load）或存储（store）操作时，CPU 将触发缺页异常（page-fault exception）。usertrap 会检查这种情况 (3372) 并调用 vmfault (1879) 来处理该缺页异常。vmfault 会检查触发异常的地址是否在之前由 sbrk 授权的区域内，使用 kalloc 分配一页物理内存，将分配的页面清零，并使用 mappages 向用户页表添加一个 PTE。Xv6 为新页面的 PTE 设置 PTE_W、PTE_R、PTE_U 和 PTE_V 标志。然后，usertrap 在引起异常的指令处恢复进程执行。由于现在 PTE 已有效，重新执行的加载或存储指令将正常运行而不再触发异常。

If an application frees memory using sbrk, sys_sbrk calls shrinkproc, which calls uvmdealloc. The real work is done by uvmunmap (1604), which uses walk to find PTEs. Since some pages may never have been used by the process and thus never have been allocated by vmfault, uvmunmap skips PTEs without the PTE_V flag. If a PTE mapping is valid, uvmunmap calls kfree to free the physical memory it refers to. Note that Xv6 uses a process’s page table not just to tell the hardware how to map user virtual addresses, but also as the only record of which physical memory pages are allocated to that process. That is the reason why freeing user memory (in uvmunmap) requires examination of the user page table.

如果应用程序使用 sbrk 释放内存，sys_sbrk 会调用 shrinkproc，进而调用 uvmdealloc。实际的工作由 uvmunmap (1604) 完成，它使用 walk 来查找 PTE。由于某些页面可能从未被进程使用过，因此从未由 vmfault 分配，所以 uvmunmap 会跳过没有 PTE_V 标志的 PTE。如果 PTE 映射有效，uvmunmap 会调用 kfree 来释放其指向的物理内存。请注意，Xv6 使用进程页表不仅是为了告诉硬件如何映射用户虚拟地址，而且将其作为分配给该进程的物理内存页的唯一记录。这就是为什么释放用户内存（在 uvmunmap 中）需要检查用户页表的原因。

## 5.3 Real world: Copy-On-Write (COW) fork

Many kernels (though not xv6) use page faults to implement copy-on-write (COW) fork. The fork system call promises that the child sees memory whose initial content is the same as the parent’s memory at the time of the fork. One way to implement this is to copy the entire memory of the parent to newly allocated physical memory for the child; this is what xv6 does. Copying can be slow, and it would be more efficient if the child could share the parent’s physical memory. A straightforward implementation of this would not work, however, since it would cause the parent and child to disrupt each other’s execution with their writes to the shared stack and heap.

许多内核（虽然不包括 xv6）使用页错误来实现写时复制（COW）fork。fork 系统调用承诺子进程看到的内存初始内容与 fork 时父进程的内存相同。实现这一点的一种方法是将父进程的全部内存复制到为子进程新分配的物理内存中；这正是 xv6 所做的。复制过程可能很慢，如果子进程能共享父进程的物理内存，效率会更高。然而，直接实现这种共享是行不通的，因为父子进程对共享栈和堆的写入会干扰彼此的执行。

Copy-on-write fork causes parent and child to safely share physical memory by appropriate use of page-table permissions and page faults. The basic plan is for the parent and child to initially share all physical pages, but for each to map them read-only (with the PTE_w flag clear). Parent and child can then read from the shared physical memory. If either writes a shared page, the RISCV CPU raises a page-fault exception. A kernel supporting COW would respond by allocating a new page of physical memory and copying the shared page into that new page. Then kernel would change the relevant PTE in the faulting process’s page table to point to the copy and to allow writes as well as reads, and then resume the faulting process at the instruction that caused the fault. Because the PTE now allows writes, the re-executed store instruction will execute without a fault, and will modify a private copy of the page rather than the shared page.

写时复制 fork 通过适当利用页表权限和页错误，使父子进程能够安全地共享物理内存。基本方案是让父子进程最初共享所有物理页，但将每个页都映射为只读（清除 PTE_W 标志）。随后，父子进程都可以从共享物理内存中读取数据。如果其中任何一方写入共享页，RISC-V CPU 就会触发页错误异常。支持 COW 的内核会通过分配一个新的物理内存页并将共享页内容复制到该新页中来做出响应。接着，内核会修改触发错误进程页表中的相关 PTE，使其指向该副本，并允许读写操作，然后在触发错误的指令处恢复该进程的执行。由于 PTE 现在允许写入，重新执行的存储（store）指令将不再触发错误，并会修改该页的私有副本而非共享页。

Copy-on-write requires book-keeping to help decide when physical pages can be freed, since each page can be referenced by a varying number of page tables depending on the history of forks, page faults, execs, and exits. This book-keeping allows an important optimization: if a process incurs a store page fault and the physical page is only referred to from that process’s page table, no copy is needed.

写时复制需要进行簿记（book-keeping）工作，以帮助决定何时可以释放物理页，因为根据 fork、页错误、exec 和 exit 的历史记录，每个物理页可能被不同数量的页表引用。这种簿记还允许一项重要的优化：如果一个进程触发了存储页错误，且该物理页仅被该进程的页表引用，则无需进行复制。

Copy-on-write makes fork faster, since fork need not copy memory. Some of the memory will have to be copied later, when written, but it’s often the case that most of the memory never has to be copied. A common example is fork followed by exec: a few pages may be written after the fork, but then the child’s exec releases the bulk of the memory inherited from the parent. Copy-on-write fork eliminates the need to ever copy this memory. Furthermore, COW fork is transparent: no modifications to applications are necessary for them to benefit.

写时复制（Copy-on-write）使 fork 变得更快，因为 fork 不再需要复制内存。虽然部分内存稍后在写入时仍需复制，但通常情况下，大部分内存永远不需要被复制。一个常见的例子是 fork 后紧接着执行 exec：在 fork 之后可能会写入少量页面，但随后子进程的 exec 就会释放从父进程继承的大部分内存。写时复制 fork 消除了复制这部分内存的必要性。此外，COW fork 是透明的：应用程序无需进行任何修改即可从中受益。

## 5.4 Real world: Demand paging

Yet another widely-used feature that exploits page faults is demand paging. In the exec system call, loads all of an application’s text and data into memory before starting the application.

另一个广泛利用页错误的特性是请求分页。在 exec 系统调用中， 会在启动应用程序之前将其所有的代码段（text）和数据段加载到内存中。

Since applications can be large and reading from disk takes time, this startup cost can be noticeable to users. To decrease startup time, a modern kernel doesn’t initially load the executable file into memory, but just creates the user page table with all PTEs marked invalid. The kernel starts the program running; each time the program uses a page for the first time, a page fault occurs, and in response the kernel reads the content of the page from disk and maps it into the user address space. Like COW fork and lazy allocation, the kernel can implement this feature transparently to applications.

由于应用程序可能很大且从磁盘读取需要时间，这种启动开销对用户来说是显而易见的。为了缩短启动时间，现代内核最初并不将可执行文件加载到内存中，而只是创建用户页表，并将所有页表项（PTE）标记为无效。内核开始运行程序；每当程序第一次使用某个页面时，就会触发页错误，作为响应，内核从磁盘读取该页面的内容并将其映射到用户地址空间。与 COW fork 和延迟分配一样，内核可以透明地为应用程序实现这一特性。

The programs running on a computer may need more memory than the computer has RAM. To cope gracefully, the operating system may implement paging to disk. The idea is to store only a fraction of user pages in RAM, and to store the rest on disk in a paging area. The kernel marks PTEs that correspond to memory stored in the paging area (and thus not in RAM) as invalid. If an application tries to use one of the pages that has been paged out to disk, the application will incur a page fault, and the page must be paged in: the kernel trap handler will allocate a page of physical RAM, read the page from disk into the RAM, and modify the relevant PTE to point to the RAM.

计算机上运行的程序所需的内存可能超过计算机拥有的 RAM 总量。为了优雅地应对这种情况，操作系统可以实现磁盘分页。其核心思想是仅在 RAM 中存储一部分用户页面，而将其余页面存储在磁盘的分页区中。内核将对应于存储在分页区（即不在 RAM 中）的内存的 PTE 标记为无效。如果应用程序尝试使用已分页到磁盘的页面，则会触发页错误，此时必须将该页换入：内核陷阱处理程序将分配一个物理 RAM 页，将该页从磁盘读取到 RAM 中，并修改相关的 PTE 以指向该 RAM。

What happens if a page needs to be paged in, but there is no free physical RAM? In that case, the kernel must first free a physical page by paging it out or evicting it to the paging area on disk, and marking the PTEs referring to that physical page as invalid. Eviction is expensive, so paging performs best if it’s infrequent: if applications use only a subset of their memory pages and the union of the subsets fits in RAM. This property is often referred to as having good locality of reference. As with many virtual memory techniques, kernels usually implement paging to disk in a way that’s transparent to applications.

如果需要换入一个页面，但物理内存已满，会发生什么？在这种情况下，内核必须首先释放一个物理页，方法是将其换出或驱逐到磁盘上的分页区，并将指向该物理页的所有页表项（PTE）标记为无效。驱逐操作代价高昂，因此只有在不频繁发生时，分页性能才最佳：即应用程序仅使用其内存页的一个子集，且这些子集的并集能容纳在物理内存中。这种特性通常被称为具有良好的引用局部性。与许多虚拟内存技术一样，内核实现磁盘分页的方式通常对应用程序是透明的。

Computers often operate with little or no free physical memory, regardless of how much RAM the hardware provides. For example, cloud providers multiplex many customers on a single machine to use their hardware cost-effectively. As another example, users run many applications on smart phones in a small amount of physical memory. In such settings allocating a page may require first evicting an existing page. Thus, when free physical memory is scarce, allocation is expensive.

无论硬件提供多少物理内存，计算机在运行时往往只有很少甚至没有空闲内存。例如，云服务提供商在单台机器上复用多个客户，以提高硬件的成本效益。又如，用户在智能手机有限的物理内存中运行许多应用程序。在这些场景下，分配一个页面可能需要先驱逐一个现有页面。因此，当空闲物理内存稀缺时，分配操作的代价是昂贵的。

Lazy allocation and demand paging are particularly advantageous when free memory is scarce and programs actively use only a fraction of their allocated memory. These techniques can also avoid the work wasted when a page is allocated or loaded but either never used or evicted before it can be used.

当空闲内存稀缺且程序仅活跃使用其分配内存的一小部分时，延迟分配和请求分页尤其具有优势。这些技术还可以避免不必要的工作，例如避免分配或加载了一个页面，但该页面从未被使用，或者在被使用前就被驱逐了。

## 5.5 Real world: Memory-mapped files

Other features that combine paging and page-fault exceptions include automatically extending stacks and memory-mapped files, which are files that a program maps into its address space using the mmap system call so that the program can read and write them using load and store instructions.

结合分页和页错误异常的其他特性还包括自动扩展栈和内存映射文件。内存映射文件是指程序使用 mmap 系统调用将其映射到自身地址空间的文件，这样程序就可以使用加载（load）和存储（store）指令对其进行读写。

## 5.6 Exercises

1. Write a user program that grows its address space by one byte by calling sbrk (1). Run the program and investigate the page table for the program before the call to sbrk and after the call to sbrk. How much space has the kernel allocated? What does the PTE for the new memory contain?
   编写一个用户程序，通过调用 sbrk(1) 将其地址空间增加一个字节。运行该程序，并研究调用 sbrk 之前和之后该程序的页表。内核分配了多少空间？新内存的页表项（PTE）包含什么内容？
2. Implement COW fork.
   实现写时复制（COW）fork。
3. Implement mmap.
   实现 mmap。

