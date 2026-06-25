---
title: xv6 riscv book chapter 4：Traps and system calls
date: 2025-07-27
tag: 
- OS
- risc-v
category: 
- OS
- risc-v
---

# xv6 riscv book chapter 4：Traps and system calls

There are three kinds of event which cause the CPU to set aside ordinary execution of instructions and force a transfer of control to special kernel code that handles the event. One situation is a system call, when a user program executes the ecall instruction to ask the kernel to do something for it. Another situation is an exception: an instruction (user or kernel) does something illegal, such as load from an invalid virtual address. The third situation is a device interrupt, when a device signals that it needs attention, for example when the disk hardware finishes a read or write request.

有三种类型的事件会导致 CPU 暂停普通的指令执行，并强制将控制权转移到处理该事件的特殊内核代码。第一种情况是系统调用，即用户程序执行 ecall 指令请求内核为其执行某些操作。第二种情况是异常：指令（用户或内核）执行了非法操作，例如从无效的虚拟地址加载数据。第三种情况是设备中断，即设备发出信号表示需要处理，例如磁盘硬件完成了读写请求。

This book uses trap as a generic term for these situations. Typically whatever code was executing at the time of the trap will later need to resume, and shouldn’t need to be aware that anything special happened. That is, we often want traps to be transparent; this is particularly important for device interrupts, which the interrupted code typically doesn’t expect. A trap forces a transfer of control into the kernel; the kernel saves registers and other state so that execution can be resumed; the kernel executes appropriate handler code (e.g., a system call implementation or device driver); the kernel restores the saved state and returns from the trap; and the original code resumes where it left off.

本书使用“陷阱”（trap）作为这些情况的通用术语。通常，在发生陷阱时正在执行的代码稍后需要恢复运行，并且不应该察觉到发生了任何特殊情况。也就是说，我们通常希望陷阱是透明的；这对于设备中断尤为重要，因为被中断的代码通常无法预料到中断的发生。陷阱会强制将控制权转移到内核中；内核保存寄存器和其他状态以便恢复执行；内核执行相应的处理程序代码（例如系统调用实现或设备驱动程序）；内核恢复保存的状态并从陷阱中返回；最后，原始代码从中断处恢复执行。

Xv6 handles all traps in the kernel; traps are not delivered to user code. Handling traps in the kernel is natural for system calls. It makes sense for interrupts since isolation demands that only the kernel be allowed to use devices, and because the kernel is able to share devices among multiple processes. It also makes sense for exceptions since the kernel may be able to handle the exception from user space (for an example see Chapter 5) or respond by killing the offending program.

Xv6 在内核中处理所有陷阱；陷阱不会被传递给用户代码。在内核中处理陷阱对于系统调用来说是很自然的。对于中断而言，这同样合理，因为隔离性要求仅允许内核使用设备，且内核能够在多个进程之间共享设备。对于异常而言，这也有其意义，因为内核可能能够处理来自用户空间的异常（示例见第 5 章），或者通过杀死违规程序来做出响应。

Xv6 trap handling proceeds in four stages: hardware actions taken by the RISC-V CPU, some assembly instructions that prepare the way for kernel C code, a C function that decides what to do with the trap, and the system call or device-driver service routine. While commonality among the three trap types suggests that a kernel could handle all traps with a single code path, it turns out to be convenient to have separate code for two distinct cases: traps from user space, and traps from kernel space. Kernel code (assembler or C) that processes a trap is often called a handler; the first handler instructions are usually written in assembler (rather than C ) and are sometimes called a vector.

Xv6 的陷阱处理分为四个阶段：RISC-V CPU 执行的硬件操作、为内核 C 代码做准备的一些汇编指令、一个决定如何处理陷阱的 C 函数，以及系统调用或设备驱动服务程序。虽然三种陷阱类型之间的共同点表明内核可以用单一代码路径处理所有陷阱，但事实证明，为两种不同情况编写独立的代码更为方便：来自用户空间的陷阱和来自内核空间的陷阱。处理陷阱的内核代码（汇编或 C）通常被称为处理程序（handler）；处理程序的第一条指令通常用汇编（而非 C）编写，有时被称为向量（vector）。

Before proceeding, please read kernel/trampoline.S, and usertrap() and prepare_return() in kernel/trap.c.

在继续之前，请阅读 kernel/trampoline.S，以及 kernel/trap.c 中的 usertrap() 和 prepare_return()。

## 4.1 RISC-V trap machinery

Each RISC-V CPU has a set of hardware control registers that the kernel writes to tell the CPU how to handle traps, and that the kernel can read to find out about a trap that has occurred. The RISC-V documents contain the full story [3]. riscv. h(0500) contains definitions that xv6 uses. Here’s an outline of the most important registers:

每个 RISC-V CPU 都有一组硬件控制寄存器，内核通过写入这些寄存器来告知 CPU 如何处理陷阱，并通过读取这些寄存器来了解已发生的陷阱。RISC-V 文档包含了完整的内容 [3]。riscv.h (0500) 包含了 xv6 使用的定义。以下是最重要寄存器的概述：

- stvec: The kernel writes the address of its trap handler code here; the RISC-V jumps to the address in stvec to handle a trap.
  stvec：内核在此处写入其陷阱处理程序（trap handler）代码的地址；RISC-V 通过跳转到 stvec 中的地址来处理陷阱。
- sepc: When a trap occurs, RISC-V saves the program counter here (since the pc is then overwritten with the value in stvec). The sret (return from trap) instruction copies sepc to the pc. The kernel can write sepc to control where sret goes.
  sepc：当陷阱发生时，RISC-V 会将程序计数器（pc）保存到此处（因为随后 pc 会被 stvec 中的值覆盖）。sret（从陷阱返回）指令会将 sepc 复制回 pc。内核可以通过写入 sepc 来控制 sret 返回的位置。
- scause: RISC-V puts a number here that describes the reason for the trap.
  scause：RISC-V 在此处放置一个数字，用于描述发生陷阱的原因。
- sscratch: The kernel trap handler code uses sscratch to help it avoid overwriting user registers before saving them.
  sscratch：内核陷阱处理程序代码使用 sscratch 来辅助其在保存用户寄存器之前避免覆盖它们。
- sstatus: The SIE bit in sstatus controls whether device interrupts are enabled. If the kernel clears SIE, the RISC-V will defer device interrupts until the kernel sets SIE. The SPP bit indicates whether a trap came from user mode or supervisor mode, and controls to what mode sret returns.
  sstatus：sstatus 中的 SIE 位控制是否启用设备中断。如果内核清除 SIE，RISC-V 将推迟设备中断，直到内核重新设置 SIE。SPP 位指示陷阱是来自用户模式还是特权模式（supervisor mode），并控制 sret 返回到哪种模式。

The above registers can only be accessed in supervisor mode (i.e., by the kernel); the CPU prevents user code from reading or writing them.

上述寄存器只能在主管模式（即由内核）访问；CPU 会阻止用户代码对其进行读写。

Each CPU on a multi-core chip has its own set of these registers, and more than one CPU may be handling a trap at any given time.

多核芯片上的每个 CPU 都有自己的一套此类寄存器，并且在任何给定时间，可能有一个以上的 CPU 正在处理陷阱（trap）。

When it forces a trap, the RISC-V hardware does the following:

当强制触发陷阱（trap）时，RISC-V 硬件会执行以下操作：

1. If the trap is a device interrupt, and the sstatus SIE bit is clear, don’t do any of the following.
   如果该陷阱是设备中断，且 sstatus 中的 SIE 位为清除状态（0），则不执行以下任何操作。
2. Disable interrupts by clearing the SIE bit in sstatus.
   通过清除 sstatus 中的 SIE 位来禁用中断。
3. Copy the pc to sepc.
   将 pc 的值复制到 sepc。
4. Save the current mode (user or supervisor) in the SPP bit in sstatus.
   将当前模式（用户模式或内核模式）保存到 sstatus 的 SPP 位中。
5. Set scause to a number indicating the trap’s cause.
   将 scause 设置为指示陷阱（trap）原因的编号。
6. Set the mode to supervisor.
   将模式设置为主管模式（supervisor mode）。
7. Copy stvec to the pc.
   将 stvec 复制到程序计数器（pc）。
8. Start executing at the new pc.
   从新的 pc 开始执行。


The CPU doesn’t switch to the kernel page table, doesn’t switch to a stack in the kernel, and doesn’t save any registers other than the pc. Kernel software must perform these tasks. One reason that the CPU does minimal work during a trap is to provide flexibility to software; for example, some operating systems omit a page table switch in some situations to increase trap performance.

CPU 不会切换到内核页表，不会切换到内核栈，也不会保存除程序计数器（pc）以外的任何寄存器。内核软件必须执行这些任务。CPU 在陷阱（trap）期间仅执行最少工作的一个原因是为软件提供灵活性；例如，某些操作系统在某些情况下会省略页表切换，以提高陷阱处理性能。

It’s worth thinking about whether any of the steps listed above could be omitted, perhaps in search of faster traps. Though there are situations in which a simpler sequence can work, many of the steps would be dangerous to omit in general. For example, suppose that the CPU didn’t switch program counters. Then a trap from user space could switch to supervisor mode while still running user instructions. Those user instructions could break user/kernel isolation, for example by modifying the satp register to point to a page table that allowed accessing all of physical memory. It is thus important that the CPU switch to a kernel-specified instruction address, namely stvec.

值得思考的是，上述步骤中是否有任何步骤可以省略，或许是为了追求更快的陷阱处理速度。虽然在某些情况下更简单的序列也能奏效，但通常情况下，省略其中许多步骤将是危险的。例如，假设 CPU 不切换程序计数器。那么来自用户空间的陷阱可能会在仍然运行用户指令的同时切换到特权模式（supervisor mode）。这些用户指令可能会破坏用户/内核隔离，例如通过修改 satp 寄存器使其指向一个允许访问所有物理内存的页表。因此，CPU 切换到内核指定的指令地址（即 stvec）至关重要。

## 4.2 Traps from user space

Xv6 handles traps differently depending on whether the trap occurs while executing in the kernel or in user code. Here is the story for traps from user code; Section 4.5 describes traps from kernel code.

Xv6 处理陷阱的方式取决于陷阱是发生在内核执行期间还是用户代码执行期间。以下是来自用户代码的陷阱处理过程；第 4.5 节描述了来自内核代码的陷阱。

A trap may occur while executing in user space if the user program makes a system call (ecall instruction), or does something illegal, or if a device interrupts. As shown in Figure 4.1, the highlevel path of a trap from user space is uservec (3071), then usertrap (3337); and when the kernel is ready to return, usertrap returns to userret (3151) which executes sret to user space.

如果用户程序执行系统调用（ecall 指令）、执行非法操作或发生设备中断，则在用户空间执行时可能会发生陷阱。如图 4.1 所示，来自用户空间的陷阱的高层路径是 uservec (3071)，然后是 usertrap (3337)；当内核准备返回时，usertrap 返回到 userret (3151)，后者执行 sret 返回到用户空间。

A major constraint on the design of xv6’s trap handling is the fact that the RISC-V hardware does not switch page tables when it forces a trap. This means that the trap handler address in stvec must have a valid mapping in the user page table, since that’s the page table in force when the trap handling code starts executing. Furthermore, xv6’s trap handling code needs to switch to the kernel page table; in order to be able to continue executing after that switch, the kernel page table must also have a mapping for the handler pointed to by stvec.

xv6 中断处理设计的一个主要限制在于，RISC-V 硬件在强制触发中断时不会切换页表。这意味着中断处理程序的地址必须在stvec 必须在用户页表中有一个有效的映射，因为当陷阱处理代码开始执行时，该页表正是当时生效的页表。此外，xv6 的陷阱处理代码需要切换到内核页表；为了在切换后能够继续执行，内核页表也必须为 stvec 指向的处理程序提供映射。

Xv6 satisfies these requirements using a trampoline page. This page contains uservec, the xv6 trap handling code that stvec points to. The trampoline page is mapped in every process’s page table at virtual address (called trampoline), which is the last page in the virtual address space so that it will be above memory that programs use for themselves. The trampoline page is mapped at the same virtual address in the kernel page table. See Figure 2.3 and Figure 3.3. Because the trampoline page is mapped in the user page table, traps can start executing there in supervisor mode. Because the trampoline page is mapped at the same address in the kernel address space, the trap handler can continue to execute after it switches to the kernel page table.

Xv6 通过使用一个“跳板”（trampoline）页来满足这些要求。该页面包含 uservec，即 stvec 指向的 xv6 陷阱处理代码。跳板页映射在每个进程页表的虚拟地址 （称为 TRAMPOLINE）处，这是虚拟地址空间中的最后一个页面，因此它位于程序自身使用的内存之上。跳板页在内核页表中也映射在相同的虚拟地址处。参见图 2.3 和图 3.3。由于跳板页映射在用户页表中，陷阱可以在监管者模式（supervisor mode）下开始在那里执行。由于跳板页在内核地址空间中映射在相同的地址，陷阱处理程序在切换到内核页表后可以继续执行。

The code for the uservec trap handler is in trampoline. S(3071). When uservec starts, all 32 registers contain values owned by the interrupted user code. These 32 values need to be saved somewhere in memory, so that later on the kernel can restore them before returning to user space. Storing to memory requires use of a register to hold the store’s destination address, but at this point there are no general-purpose registers available! Luckily RISC-V provides a helping hand in the form of the sscratch register. The csrw instruction at the start of uservec saves a 0 in sscratch. Now uservec has one register (a 0 ) to play with. uservec’s next task is to save the 32 user registers. The kernel allocates, for each process, a page of memory for a trapframe structure that (among other things) has space to save the 32 user registers (1992). Because satp still refers to the user page table, uservec needs the trapframe to be mapped in the user address space. Xv6 maps each process’s trapframe at virtual address TRAPFRAME ( ) in that process’s user page table; one page below TRAMPOLINE. Each process’s p->trapframe contains a kernel virtual address for the process’s trapframe. uservec sets register a 0 to address TRAPFRAME and saves all the user registers there. Then it retrieves the user a 0 from sscratch and saves it in the trapframe.

uservec 陷阱处理程序的代码位于 trampoline.S (3071) 中。当 uservec 开始运行时，所有 32 个寄存器都包含被中断的用户代码所拥有的值。这 32 个值需要保存到内存中的某个地方，以便稍后内核在返回用户空间之前可以恢复它们。向内存存储数据需要使用一个寄存器来保存存储的目标地址，但此时没有可用的通用寄存器！幸运的是，RISC-V 以 sscratch 寄存器的形式提供了帮助。uservec 开头的 csrw 指令将 a0 的值保存在 sscratch 中。现在 uservec 有一个寄存器（a0）可以使用了。uservec 的下一个任务是保存 32 个用户寄存器。内核为每个进程分配一个内存页作为 trapframe 结构，该结构（除其他内容外）有空间保存 32 个用户寄存器 (1992)。由于 satp 仍然指向用户页表，uservec 需要将 trapframe 映射在用户地址空间中。Xv6 将每个进程的 trapframe 映射在该进程用户页表的虚拟地址 TRAPFRAME ( ) 处；即 TRAMPOLINE 下方的一个页面。每个进程的 p->trapframe 包含该进程 trapframe 的内核虚拟地址。uservec 将寄存器 a0 设置为地址 TRAPFRAME，并将所有用户寄存器保存在那里。然后，它从 sscratch 中取回用户的 a0 值，并将其保存在 trapframe 中。

The kernel previously initialized the trapframe to contain some values useful to uservec: the address of the current process’s kernel stack, the current CPU’s hartid, the address of the usertrap function, and the address of the kernel page table. uservec retrieves these values, switches satp to the kernel page table, and jumps to usertrap, a C function.

内核此前已初始化了 trapframe，使其包含一些对 uservec 有用的值：当前进程内核栈的地址、当前 CPU 的 hartid、usertrap 函数的地址以及内核页表的地址。uservec 获取这些值，将 satp 切换为内核页表，并跳转到 C 函数 usertrap。

The job of usertrap is to determine the cause of the trap, process it, and return (3337). It first changes stvec so that a trap while in the kernel will be handled by kernelvec rather than uservec. It saves the sepc register (the saved user program counter) for future use when returning back to user space. If the trap is a system call, usertrap calls syscall to handle it; if a device interrupt, devintr; if a page fault, vmfault; otherwise it’s an exception (e.g., use of an invalid address), and the kernel kills the faulting process. The system call path adds four to the saved user program counter because RISC-V, in the case of a system call, leaves the program pointer pointing to the ecall instruction but user code needs to resume executing at the subsequent instruction. usertrap checks if the process has been killed or should yield the CPU (if this trap is a timer interrupt).

usertrap 的任务是确定陷阱（trap）的原因，对其进行处理并返回 (3337)。它首先修改 stvec，以便在内核中发生的陷阱由 kernelvec 而非 uservec 处理。它保存 sepc 寄存器（保存的用户程序计数器），以便后续返回用户空间时使用。如果陷阱是系统调用，usertrap 调用 syscall 来处理；如果是设备中断，则调用 devintr；如果是缺页异常，则调用 vmfault；否则它就是一个异常（例如使用无效地址），内核将杀死产生故障的进程。系统调用路径会将保存的用户程序计数器加 4，因为在发生系统调用时，RISC-V 会让程序指针指向 ecall 指令，但用户代码需要从下一条指令恢复执行。usertrap 还会检查进程是否已被杀死或是否应该让出 CPU（如果该陷阱是定时器中断）。

The first step in returning to user space is the call to prepare_return (3404). This function sets up the RISC-V control registers to prepare for a future trap from user space: setting stvec to uservec and preparing the trapframe fields that uservec relies on. prepare_return sets sepc to the previously saved user program counter. Finally, usertrap returns back to userret in the trampoline page (3151), passing back a pointer to the user page table in a 0 . userret switches satp to the process’s user page table. Recall that the user page table maps both the trampoline page and TRAPFRAME, but nothing else from the kernel. The trampoline page mapping at the same virtual address in user and kernel page tables allows userret to keep executing after changing satp. From this point on, the only data userret can use is the register contents and the content of the trapframe. userret loads the TRAPFRAME address into a 0 , restores saved user registers from the trapframe via a 0 , restores the saved user a 0 , and executes sret to return to user space. uservec and userret are written in assembly language because it is difficult to write C code to save or restore all the registers or survive switching page tables.

返回用户空间的第一步是调用 prepare_return (3404)。该函数prepare_return 设置 RISC-V 控制寄存器，为未来来自用户空间的陷阱做准备：将 stvec 设置为 uservec，并准备 uservec 所依赖的 trapframe 字段。prepare_return 将 sepc 设置为之前保存的用户程序计数器。最后，usertrap 返回到 trampoline 页中的 userret (3151)，并将指向用户页表的指针通过 a0 传递回去。userret 将 satp 切换为进程的用户页表。回想一下，用户页表映射了 trampoline 页和 TRAPFRAME，但没有映射内核的其他任何内容。trampoline 页在用户页表和内核页表中映射到相同的虚拟地址，这使得 userret 在更改 satp 后能继续执行。从此时起，userret 唯一能使用的数据是寄存器内容和 trapframe 的内容。userret 将 TRAPFRAME 地址加载到 a0，通过 a0 从 trapframe 中恢复保存的用户寄存器，恢复保存的用户 a0，最后执行 sret 返回用户空间。uservec 和 userret 是用汇编语言编写的，因为很难编写 C 代码来保存或恢复所有寄存器，或者在切换页表后继续运行。

## 4.3 Code: Calling system calls

User programs call library functions in order to make system calls. For example, the shell displays a prompt with this function call (in user/sh.c): write(2, "$ ", 2); Here’s the library function, in user/usys. S:

用户程序通过调用库函数来发起系统调用。例如，shell 使用以下函数调用（位于 `user/sh.c` 中）来显示提示符：以下是位于 user/usys.S 中的库函数：

```c
write:
    li a7, SYS_write
    ecall
    ret
```

The code that the C compiler generates for the function call loads the three arguments into registers a0, a1, and a2. Then the write() function loads the system call number, SYS_write (16), into a 7. The kernel will look at those registers to find out what system call is intended, and what the arguments are. The ecall instruction traps from user space into the kernel and causes uservec, usertrap, and then syscall to execute.

C 编译器为该函数调用生成的代码会将三个参数加载到寄存器 a0、a1 和 a2 中。随后，write() 函数将系统调用号 SYS_write (16) 加载到 a7 中。内核将通过检查这些寄存器来确定预期的系统调用及其参数。ecall 指令会从用户空间陷入（trap）内核，并触发 uservec、usertrap，接着执行 syscall。

At this point, please read kernel/syscall.c,sys_write() in kernel/sysfile.c, and copyout(), copyin(), and copyinstr() in kernel/vm.c. syscall (3731) retrieves the system call number from the saved a 7 in the trapframe and uses it to index into syscalls (3706). For our example, a 7 contains SYS_write (3566), resulting in a call to the system call implementation function sys_write.

此时，请阅读 kernel/syscall.c、kernel/sysfile.c 中的 sys_write()，以及 kernel/vm.c 中的 copyout()、copyin() 和 copyinstr()。syscall (3731) 从 trapframe 中保存的 a7 寄存器里获取系统调用号，并以此作为索引访问 syscalls (3706)。在我们的示例中，a7 包含 SYS_write (3566)，从而导致调用系统调用的实现函数 sys_write。

When sys_write returns, syscall records its return value in p->trapframe->a0. This will cause the original user-space call to write () to return that value, since the C calling convention on RISC-V places return values in a 0 . System calls conventionally return negative numbers to indicate errors, and zero or positive numbers for success.

当 sys_write 返回时，syscall 会将其返回值记录在 p->trapframe->a0 中。这将导致用户空间原始的 write() 调用返回该值，因为 RISC-V 上的 C 语言调用约定将返回值放在 a0 中。按照惯例，系统调用返回负数表示错误，返回零或正数表示成功。

## 4.4 Code: System call arguments

System call arguments start out in the user registers, and are then moved to the trap frame by the kernel trap code. The kernel functions argint, argaddr, and argfd retrieve the 'th system call argument from the trap frame as an integer, pointer, or a file descriptor.

系统调用参数最初存放在用户寄存器中，随后由内核陷阱代码移动到陷阱帧（trap frame）中。内核函数 argint、argaddr 和 argfd 分别从陷阱帧中以整数、指针或文件描述符的形式检索第 个系统调用参数。

Some system calls pass pointers as arguments, and the kernel must use those pointers to read or write user memory. The write system call, for example, passes the kernel a user-space pointer to the data to be written. Such pointers pose two challenges. First, the user program may be buggy or malicious, and may pass the kernel an invalid pointer or a pointer intended to trick the kernel into accessing kernel memory instead of user memory. Second, the xv6 kernel page table mappings are not the same as the user page table mappings, so the kernel cannot use ordinary instructions to load or store from user-supplied addresses.

某些系统调用将指针作为参数传递，内核必须使用这些指针来读取或写入用户内存。例如，write 系统调用向内核传递一个指向待写入数据的用户空间指针。此类指针带来了两个挑战。首先，用户程序可能存在漏洞或具有恶意，可能会向内核传递一个无效指针，或者传递一个旨在诱导内核访问内核内存而非用户内存的指针。其次，xv6 内核页表映射与用户页表映射不同，因此内核无法使用普通指令从用户提供的地址进行加载或存储。

The kernel implements functions that safely transfer data to and from user-supplied addresses. fetchstr is an example (3624). File system calls such as exec use fetchstr to retrieve string file-name arguments from user space. fetchstr calls copyinstr to do the hard work. copyinstr (1833) copies up to max bytes to dst from virtual address srcva in the user page table pagetable. Since pagetable is not the current page table, copyinstr uses walkaddr (which calls walk) to look up srcva in pagetable, yielding physical address pa0. The kernel’s page table maps all of physical RAM at virtual addresses that are equal to the RAM’s physical address. This allows copyinstr to directly copy string bytes from pa0 to dst. walkaddr (1520) checks that the user-supplied virtual address is part of the process’s user address space, so programs cannot trick the kernel into reading other memory. A similar function, copyout, copies data from the kernel to a user-supplied address.

内核实现了安全地在用户提供地址之间传输数据的函数。fetchstr 就是一个例子 (3624)。诸如 exec 之类的文件系统调用使用 fetchstr 从用户空间检索字符串文件名参数。fetchstr 调用 copyinstr 来完成核心工作。copyinstr (1833) 从用户页表 pagetable 中的虚拟地址 srcva 复制最多 max 字节到 dst。由于 pagetable 不是当前的页表，copyinstr 使用 walkaddr（它会调用 walk）在 pagetable 中查找 srcva，从而得到物理地址 pa0。内核页表将所有物理内存映射到与物理地址相等的虚拟地址上。这使得 copyinstr 能够直接将字符串字节从 pa0 复制到 dst。walkaddr (1520) 会检查用户提供的虚拟地址是否属于进程的用户地址空间，因此程序无法诱骗内核读取其他内存。一个类似的函数 copyout 则负责将数据从内核复制到用户提供的地址。

## 4.5 Traps from kernel space

Please read kernel/kernelvec.S, and kerneltrap() in kernel/trap.c. Xv6 handles traps from kernel code in a different way than traps from user code. When entering the kernel, usertrap points stvec to the assembly code at kernelvec (3211), Since kernelvec only executes if xv6 was already in the kernel, kernelvec can rely on satp being set to the kernel page table, and on the stack pointer referring to a valid kernel stack. kernelvec pushes all 32 registers onto the current stack, from which it will later restore them so that the interrupted kernel code can resume without disturbance. kernelvec saves the registers on the stack of the interrupted kernel thread, which makes sense because the register values belong to that thread. This is particularly important if the trap causes a switch to a different thread - in that case the trap will actually return from the stack of the new thread, leaving the interrupted thread’s saved registers safely on its stack. kernelvec jumps to kerneltrap (3453) after saving registers. kerneltrap is prepared for just one type of trap: device interrupts. It calls devintr (3506) to handle them. If the trap isn’t a device interrupt, it must be an exception, such as kernel code trying to use an invalid pointer. This could only be caused by a bug in the kernel code. The kernel does not have a way to recover in this situation, so it calls panic(), which prints an error message and then halts.

请阅读 `kernel/kernelvec.S` 以及 `kernel/trap.c` 中的 `kerneltrap()`。Xv6 处理来自内核代码的陷阱的方式与来自用户代码的陷阱不同。当进入内核时，usertrap 将 stvec 指向 kernelvec (3211) 处的汇编代码。由于只有在 xv6 已经处于内核态时才会执行 kernelvec，因此 kernelvec 可以依赖于 satp 已设置为内核页表，并且栈指针指向一个有效的内核栈。kernelvec 将所有 32 个寄存器推入当前栈中，稍后将从栈中恢复这些寄存器，以便被中断的内核代码可以无干扰地恢复运行。kernelvec 将寄存器保存在被中断的内核线程的栈上，这是合理的，因为寄存器值属于该线程。如果陷阱导致切换到另一个线程，这一点尤为重要——在这种情况下，陷阱实际上会从新线程的栈中返回，而被中断线程保存的寄存器则安全地保留在其自身的栈上。kernelvec 在保存寄存器后跳转到 kerneltrap (3453)。kerneltrap 仅准备处理一种类型的陷阱：设备中断。它调用 devintr (3506) 来处理它们。如果陷阱不是设备中断，那么它一定是异常，例如内核代码尝试使用无效指针。这只能是由内核代码中的错误引起的。内核在这种情况下没有恢复的方法，因此它调用 panic()，打印错误消息然后停机。

If kerneltrap was called due to a timer interrupt, and a process’s kernel thread is running (as opposed to a scheduler thread), kerneltrap calls yield to give other threads a chance to run. At some point one of those threads will yield, and let our thread and its kerneltrap resume again. Chapter 8 explains what happens in yield.

如果 `kerneltrap` 是由于定时器中断被调用的，并且当前正在运行的是进程的内核线程（而非调度器线程），`kerneltrap` 会调用 `yield` 以给其他线程运行的机会。在某个时刻，那些线程中的一个会主动让出 CPU，从而让我们的线程及其 `kerneltrap` 再次恢复执行。第 8 章将解释 `yield` 中发生了什么。

When kerneltrap’s work is done, it needs to return to whatever code was interrupted by the trap. Because a yield may have disturbed sepc and the previous mode in sstatus, kerneltrap saves them when it starts. It now restores those control registers and returns to kernelvec (3237). kernelvec pops the saved registers from the stack and executes sret, which copies sepc to pc and resumes the interrupted kernel code.

当 `kerneltrap` 的工作完成后，它需要返回到被陷阱（trap）中断的代码处。由于 `yield` 可能会干扰 `sepc` 和 `sstatus` 中的前一个模式，`kerneltrap` 在开始时会保存它们。现在它恢复这些控制寄存器并返回到 `kernelvec` (3237)。`kernelvec` 从栈中弹出保存的寄存器并执行 `sret`，该指令将 `sepc` 复制到 `pc` 并恢复执行被中断的内核代码。

Xv6 sets a CPU’s stvec to kernelvec when that CPU enters the kernel from user space; you can see this in usertrap (3346). But there’s a window of time when the kernel has started executing but stvec is still set to uservec, and it’s crucial that no device interrupt occur during that window. Luckily the RISC-V always disables interrupts when it starts to take a trap, and usertrap doesn’t enable them again until after it sets stvec.

当 CPU 从用户空间进入内核时，xv6 会将该 CPU 的 `stvec` 设置为 `kernelvec`；你可以在 `usertrap` (3346) 中看到这一点。但在内核开始执行到 `stvec` 被设置为 `uservec` 之间存在一个时间窗口，在这个窗口期间绝对不能发生设备中断，这一点至关重要。幸运的是，RISC-V 在开始处理陷阱时总是会禁用中断，而 `usertrap` 直到设置完 `stvec` 之后才会再次启用中断。

## 4.6 Real world

The need for trampoline pages could be eliminated if kernel memory were mapped into every process’s user page table (with PTE_U clear). That would also eliminate the need for a page table switch when trapping from user space into the kernel. That in turn would allow system call implementations in the kernel to take advantage of the current process’s user memory being mapped, allowing kernel code to directly dereference user pointers. Many operating systems have used these ideas to increase efficiency. Xv6 avoids them in order to reduce the chances of security bugs in the kernel due to inadvertent use of user pointers, and to reduce some complexity that would be required to ensure that user and kernel virtual addresses don’t overlap.

如果将内核内存映射到每个进程的用户页表中（且不设置 `PTE_U` 标志），就可以消除对跳板页（trampoline pages）的需求。这还可以消除从用户空间陷阱进入内核时切换页表的必要。这反过来又允许内核中的系统调用实现利用当前进程已映射的用户内存，从而允许内核代码直接解引用用户指针。许多操作系统都利用这些想法来提高效率。xv6 避免使用这些方法，是为了减少因无意中使用用户指针而导致内核安全漏洞的可能性，并降低确保用户和内核虚拟地址不重叠所需的复杂性。

## 4.7 Exercises

1. Could some or all of the code in trampoline. and kernelvec. be written in rather than assembler?
   trampoline.S 和 kernelvec.S 中的部分或全部代码能否用 C 语言编写，而不是汇编语言？
2. Is there a way to eliminate the special TRAPFRAME page mapping in every user address space? For example, could uservec be modified to simply push the 32 user registers onto the kernel stack, or store them in the proc structure?
   有没有办法取消每个用户地址空间中特殊的 TRAPFRAME 页面映射？例如，是否可以修改 uservec，使其简单地将 32 个用户寄存器压入内核栈，或者将它们存储在 proc 结构体中？
3. Could xv 6 be modified to eliminate the special TRAMPOLINE page mapping?
   能否通过修改 xv6 来取消特殊的 TRAMPOLINE 页面映射？

