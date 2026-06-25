---
title: xv6 riscv book chapter 8：Scheduling
date: 2025-07-27
tag: 
- OS
- risc-v
category: 
- OS
- risc-v
---

# xv6 riscv book chapter 8：Scheduling

Any operating system is likely to run with more processes than the computer has CPUs, so a plan is needed to time-share the CPUs among the processes. Ideally the sharing would be transparent to user processes. A common approach is to provide each process with the illusion that it has its own virtual CPU by multiplexing the processes onto the hardware CPUs. This chapter explains how xv6 achieves this multiplexing.

任何操作系统运行的进程数都可能多于计算机拥有的 CPU 数量，因此需要一个方案在进程之间分时共享 CPU。理想情况下，这种共享对用户进程应该是透明的。一种常见的方法是通过将进程复用到硬件 CPU 上，为每个进程提供拥有独立虚拟 CPU 的假象。本章将解释 xv6 是如何实现这种复用的。

Before proceeding with this chapter, please read kernel/proc.h, kernel/swtch.S, and yield(), sched(), and schedule() in kernel/proc.c.

在继续阅读本章之前，请阅读 kernel/proc.h、kernel/swtch.S，以及 kernel/proc.c 中的 yield()、sched() 和 scheduler()。

## 8.1 Multiplexing

Xv6 multiplexes by switching each CPU from one process to another in two situations. First, xv6 switches when a process makes a system call that blocks (has to wait), for example read or wait. Second, xv6 periodically forces a switch to cope with processes that compute for long periods without blocking. The former are called voluntary switches, the latter involuntary.

Xv6 通过在两种情况下将每个 CPU 从一个进程切换到另一个进程来实现多路复用。首先，当进程发起阻塞（必须等待）的系统调用（例如 read 或 wait）时，xv6 会进行切换。其次，xv6 会定期强制切换，以应对那些长时间计算而不阻塞的进程。前者被称为主动切换，后者被称为被动切换。

Implementing multiplexing poses a few challenges. First, how to switch from one process to another? The basic idea is to save and restore CPU registers, though the fact that this cannot be expressed in C makes it tricky. Second, how to force switches in a way that is transparent to user processes? Xv6 uses the standard technique in which a hardware timer’s interrupts drive context switches. Third, all of the CPUs switch among the same set of processes, so a locking plan is necessary to avoid mistakes such as two CPUs deciding to run the same process at the same time. Fourth, a process’s memory and other resources must be freed when the process exits, but it cannot finish all of this itself. Fifth, each CPU of a multi-core machine must remember which process it is executing so that system calls affect the correct process’s kernel state.

实现多路复用面临着一些挑战。首先，如何从一个进程切换到另一个进程？基本思路是保存和恢复 CPU 寄存器，但由于这无法用 C 语言表达，因此处理起来比较棘手。其次，如何以对用户进程透明的方式强制切换？Xv6 使用了标准技术，即通过硬件定时器中断来驱动上下文切换。第三，所有的 CPU 都在同一组进程之间切换，因此需要一套锁机制来避免错误，例如两个 CPU 同时决定运行同一个进程。第四，当进程退出时，必须释放其内存和其他资源，但进程本身无法独立完成所有这些工作。第五，多核机器的每个 CPU 必须记住它正在执行哪个进程，以便系统调用能影响正确进程的内核状态。

## 8.2 Context switch overview

The term “context switch” refers to the steps involved in a CPU leaving off execution of one kernel thread (usually for later resumption), and resuming execution of a different kernel thread; this

“上下文切换”一词是指 CPU 停止执行一个内核线程（通常是为了稍后恢复）并恢复执行另一个内核线程所涉及的步骤；这


switching is the heart of multiplexing. Xv6 does not directly context switch from one process’s kernel thread to another process’s kernel thread; instead, a kernel thread gives up the CPU by context-switching to that CPU’s “scheduler thread,” and the scheduler thread picks a different process’s kernel thread to run, and context-switches to that thread.

切换是多路复用的核心。Xv6 并不直接从一个进程的内核线程上下文切换到另一个进程的内核线程；相反，内核线程通过上下文切换到该 CPU 的“调度器线程”来放弃 CPU，然后调度器线程选择另一个进程的内核线程来运行，并上下文切换到该线程。

At a broader scope, the steps involved in switching from one user process to another are illustrated in Figure 8.1, a trap (system call or interrupt) from the old process’s user space to its kernel thread, a context switch to the current CPU’s scheduler thread, a context switch to a new process’s kernel thread, and a trap return to the user-level process.

从更宏观的角度来看，图 8.1 展示了从一个用户进程切换到另一个用户进程所涉及的步骤：从旧进程的用户空间陷阱（系统调用或中断）进入其内核线程，上下文切换到当前 CPU 的调度器线程，上下文切换到新进程的内核线程，最后陷阱返回到用户级进程。

## 8.3 Code: Context switching

The function swtch() in kernel/swtch. S contains the heart of thread context switching: it saves the switched-from thread’s CPU registers, and restores the previously-saved registers of the switched-to thread. The basic reason this is sufficient is that a thread’s state consist of data in memory (e.g. its stack) plus its CPU registers; thread memory need not saved and restored because different threads keep their data in different areas of RAM; but the CPU has only one set of registers so they must be switched (saved and restored) between threads.

kernel/swtch.S 中的 swtch() 函数包含了线程上下文切换的核心：它保存被切换出的线程的 CPU 寄存器，并恢复之前保存的被切换入的线程的寄存器。之所以这样做就足够了，根本原因在于线程的状态由内存中的数据（例如其栈）加上其 CPU 寄存器组成；线程内存不需要保存和恢复，因为不同的线程将其数据保存在 RAM 的不同区域；但 CPU 只有一组寄存器，因此必须在线程之间进行切换（保存和恢复）。

Each thread’s struct proc includes a struct context that holds the thread’s saved registers when it is not running. A CPU’s scheduler thread’s struct context is in that CPU’s struct cpu. When thread wishes to switch to thread , thread calls swtch ( & s context, &Y’s context). swtch() saves the current CPU registers in X’s context, then loads the content of Y’s context into the CPU registers, then returns.

每个线程的 struct proc 都包含一个 struct context，用于在线程不运行时保存其寄存器。CPU 调度器线程的 struct context 则位于该 CPU 的 struct cpu 结构中。当线程 希望切换到线程 时，线程 会调用 swtch ( & s context, &Y’s context)。swtch() 将当前的 CPU 寄存器保存到 X 的上下文中，然后将 Y 的上下文内容加载到 CPU 寄存器中，最后返回。

Here’s an abbreviated copy of swtch:

以下是 swtch 的简略副本：

```c
swtch:
    sd ra, 0(a0)
    sd sp, 8(a0)
    sd s0, 16(a0)
    ...
sd s11, 104(a0)
ld ra, 0(a1)
ld sp, 8(a1)
ld s0, 16(a1)
\text { ⋯⋯}
ld s11, 104(a1)
ret
```

a 0 holds the first function argument, and a 1 the second; in this case, the two struct context pointers. refers to an offset 16 bytes into the memory pointed to by a 0 ; referring to the definition of struct context in kernel/proc.h (1951), this is the structure field called s0.

a 0 存放第一个函数参数，a 1 存放第二个参数；在本例中，即两个 struct context 指针。 指向 a 0 所指内存中偏移 16 字节的位置；参考 kernel/proc.h (1951) 中 struct context 的定义，这就是名为 s0 的结构体字段。

Where does swtch’s ret return to? It returns to the instruction that the ra register points to. In the example in which thread X calls swtch () to switch to Y , when ret executes, ra has just been loaded from Y’s struct context. And the ra in Y’s struct context was originally saved by Y’s call to swtch when Y gave up the CPU in the past. So the ret returns to the instruction after the point at which Y called swtch (); that is, X 's call to swtch () returns as if returning from Y’s original call to swtch (). And sp will be Y’s stack pointer, since swtch loaded sp from Y’s struct context; thus on return, Y will execute on its own stack. swtch () need not directly save or restore the program counter; it’s enough to save and restore ra. swtch (2902) saves callee-saved registers (ra, sp, s ) but not caller-saved registers. The RISC-V calling convention requires that if code needs to preserve the value in a caller-saved register across a function call, the compiler must generate instructions that save the register to the stack before the function call, and restore from the stack when the function returns. So swtch can rely on the function that called it having already saved the caller-saved registers (either that, or the calling function didn’t need the values in the registers).

swtch 的 ret 指令返回到哪里？它返回到 ra 寄存器所指向的指令。在线程 X 调用 swtch () 切换到 Y 的例子中，当 ret 执行时，ra 刚刚从 Y 的 struct context 中加载。而 Y 的 struct context 中的 ra，是过去 Y 放弃 CPU 时通过调用 swtch 保存的。因此，ret 返回到 Y 调用 swtch () 之后的指令；也就是说，X 对 swtch () 的调用返回时，就好像是从 Y 原本对 swtch () 的调用中返回一样。由于 swtch 从 Y 的 struct context 中加载了 sp，因此 sp 将是 Y 的栈指针；于是返回后，Y 将在自己的栈上执行。swtch () 不需要直接保存或恢复程序计数器（PC）；只需保存和恢复 ra 即可。swtch (2902) 保存被调用者保存寄存器（callee-saved registers，如 ra, sp, s ），但不保存调用者保存寄存器（caller-saved registers）。RISC-V 调用约定规定，如果代码需要在函数调用期间保留调用者保存寄存器中的值，编译器必须生成指令，在函数调用前将寄存器保存到栈中，并在函数返回时从栈中恢复。因此，swtch 可以假定调用它的函数已经保存了调用者保存寄存器（或者调用函数并不需要这些寄存器中的值）。

## 8.4 Code: Scheduling

The last section looked at the internals of swtch; now let’s take swtch as a given and examine switching from one process’s kernel thread through the scheduler to another process. The scheduler exists in the form of a special thread per CPU, each running the scheduler function. This function is in charge of choosing which process to run next. Each CPU has its own scheduler thread because more than one CPU may be looking for something to run at any given time. Process switching always goes through the scheduler thread, rather than direct from one process to another, to avoid some situations in which there would be no stack on which to execute the scheduler (e.g. if the old process has exited, or there is no other process that currently wants to run).

上一节探讨了 swtch 的内部实现；现在我们将 swtch 视为一个既定的功能，并研究如何从一个进程的内核线程通过调度器切换到另一个进程。调度器以每个 CPU 一个特殊线程的形式存在，每个线程都运行 scheduler 函数。该函数负责选择下一个要运行的进程。每个 CPU 都有自己的调度器线程，因为在任何给定时间，可能有一个以上的 CPU 正在寻找可运行的任务。进程切换总是通过调度器线程进行，而不是直接从一个进程切换到另一个进程，这是为了避免在某些情况下没有栈来执行调度程序（例如，如果旧进程已经退出，或者当前没有其他进程想要运行）。

A process that wants to give up the CPU must acquire its own process lock , release any other locks it is holding, update its own state ( p ->state), and then call sched. You can see

一个想要放弃 CPU 的进程必须获取它自己的进程锁 ，释放它持有的任何其他锁，更新它自己的状态（p->state），然后调用 sched。你可以看到

```c
acquire(&p->lock);
...
p->state = RUNNABLE;
swtch(&p->context, ...);
swtch(...); // return
        release(&p->lock);
        // find a RUNNABLE p
    acquire(&p->lock);
    p->state = RUNNING;
    swtch(...,&p->context);
swtch(&p->context,...); // return
        release(&p->lock);
```

Figure 8.2: swtch () always has the scheduler thread as either source or destination, and the relevant lock is always held. this sequence in yield (2629), sleep and kexit. sched calls swtch to save the current context in p->context and switch to the scheduler context in cpu->context. swtch returns on the scheduler’s stack as though scheduler’s swtch had returned (2582). scheduler (2558) runs a loop: find a process to run, swtch () to it, eventually it will swtch () back to the scheduler, which continues its loop. The scheduler loops over the process table looking for a runnable process, one that has state RUNNABLE. Once it finds a process, it sets the per-CPU current process variable proc, marks the process as RUNNING, and then calls swtch to start running it (2577-2582). At some point in the past, the target process must have called swtch () ; the scheduler’s call to swtch () effectively returns from that earlier call. Figure 8.2 illustrates this pattern. xv6 holds lock across calls to swtch: the caller of swtch acquires the lock, but it’s released in the target after swtch returns. This arrangement is unusual: it’s more common for the thread that acquires a lock to also release it. Xv6’s context switching breaks this convention because state and context must be updated together atomically. For example, if lock were released before invoking swtch, a different CPU might decide to run the process because its state is RUNNABLE. CPU will invoke swtch which will restore from ->context while the original CPU is still saving into p ->context. The result would be that the process would be restored with partially-saved registers on CPU and that both CPUs will be using the same stack, which would cause chaos. Once yield has started to modify a running process’s state to make it RUNNABLE, must remain held until the process has saved all its registers and the scheduler is running on its stack. The earliest correct release point is after scheduler (running on its own stack) clears c->proc. Similarly, once scheduler starts to convert a RUNNABLE process to

图 8.2：swtch() 总是以调度器线程作为源或目的地，并且始终持有相关的 锁。这一序列出现在 yield (2629)、sleep 和 kexit 中。sched 调用 swtch 将当前上下文保存到 p->context 中，并切换到 cpu->context 中的调度器上下文。swtch 在调度器的栈上返回，就像调度器的 swtch 调用返回了一样 (2582)。scheduler (2558) 运行一个循环：寻找一个可运行的进程，通过 swtch() 切换到该进程，最终该进程会通过 swtch() 切换回调度器，调度器随后继续其循环。调度器遍历进程表寻找一个处于可运行状态（即 state 为 RUNNABLE）的进程。一旦找到，它会设置当前 CPU 的进程变量 proc，将该进程标记为 RUNNING，然后调用 swtch 开始运行它 (2577-2582)。在过去的某个时刻，目标进程一定调用过 swtch()；调度器对 swtch() 的调用实际上是从那次早期的调用中返回。图 8.2 展示了这种模式。xv6 在调用 swtch 的过程中持有 lock：swtch 的调用者获取锁，但在 swtch 返回后由目标进程释放。这种安排很不寻常：通常情况下，获取锁的线程也负责释放它。xv6 的上下文切换打破了这一惯例，因为 state 和 context 必须原子地一起更新。例如，如果在调用 swtch 之前释放了 lock，另一个 CPU 可能会因为该进程的状态是 RUNNABLE 而决定运行它。CPU 将调用 swtch，从 ->context 恢复寄存器，而原始 CPU 仍在向 p->context 保存寄存器。结果将是该进程在 CPU 上以部分保存的寄存器恢复运行，且两个 CPU 将使用同一个栈，这会导致混乱。一旦 yield 开始修改运行中进程的状态使其变为 RUNNABLE， 必须保持持有状态，直到该进程保存了所有寄存器且调度器已在其自身的栈上运行。最早的正确释放点是在调度器（在其自身的栈上运行）清除 c->proc 之后。类似地，一旦调度器开始将一个 RUNNABLE 进程转换为

RUNNING, the lock cannot be released until the process’s kernel thread is completely running (after the swtch, for example in yield).

RUNNING，直到该进程的内核线程完全运行（在 swtch 之后，例如在 yield 中）之前，不能释放该锁。

There is one case when the scheduler’s call to swtch does not end up in sched. allocproc sets the context ra register of a new process to forkret (2653), so that its first swtch “returns” to the start of that function. forkret exists to release the p->lock and set up some control registers and trapframe fields that are required in order to return to user space. At the end, forkret simulates the normal return path from a system call back to user space.

有一种情况，调度器对 swtch 的调用最终不会进入 sched。allocproc 将新进程的 context ra 寄存器设置为 forkret (2653)，因此它的第一次 swtch 会“返回”到该函数的开头。forkret 的存在是为了释放 p->lock，并设置返回用户空间所需的一些控制寄存器和 trapframe 字段。最后，forkret 模拟了从系统调用返回到用户空间的正常路径。

## 8.5 Code: mycpu and myproc

Xv6 often needs a pointer to the current process’s proc structure. On a uniprocessor one could have a global variable pointing to the current proc. This doesn’t work on a multi-core machine, since each CPU executes a different process. The way to solve this problem is to exploit the fact that each CPU has its own set of registers.

Xv6 经常需要指向当前进程 proc 结构的指针。在单处理器上，可以使用一个全局变量指向当前 proc。但这在多核机器上行不通，因为每个 CPU 都在执行不同的进程。解决这个问题的方法是利用每个 CPU 都有自己的一组寄存器这一事实。

While a given CPU is executing in the kernel, xv6 ensures that the CPU’s tp register always holds the CPU’s hartid. RISC-V numbers its CPUs, giving each a unique hartid. mycpu (2178) uses tp to index an array of cpu structures and return the one for the current CPU. A struct cpu (1971) holds a pointer to the proc structure of the process currently running on that CPU (if any), saved registers for the CPU’s scheduler thread, and the count of nested spinlocks needed to manage interrupt disabling.

当某个 CPU 在内核中执行时，xv6 确保该 CPU 的 tp 寄存器始终持有该 CPU 的 hartid。RISC-V 对其 CPU 进行编号，为每个 CPU 分配一个唯一的 hartid。mycpu (2178) 使用 tp 作为索引来访问 cpu 结构体数组，并返回当前 CPU 对应的结构体。一个 struct cpu (1971) 包含了指向该 CPU 当前运行进程（如果有）的 proc 结构的指针、该 CPU 调度器线程的保存寄存器，以及用于管理中断禁用的嵌套自旋锁计数。

Ensuring that a CPU’s tp holds the CPU’s hartid is a little involved, since user code is free to modify tp. start sets the tp register early in the CPU’s boot sequence, while still in machine mode (1094). While preparing to return to user space, prepare_return saves tp in the trampoline page, in case user code modifies it. Finally, uservec restores that saved tp when entering the kernel from user space (3127). The compiler guarantees never to modify tp in kernel code. It would be more convenient if xv6 could ask the RISC-V hardware for the current hartid whenever needed, but RISC-V allows that only in machine mode, not in supervisor mode.

确保 CPU 的 tp 持有该 CPU 的 hartid 稍微有些复杂，因为用户代码可以随意修改 tp。start 在 CPU 启动序列的早期、仍处于机器模式（machine mode）时设置 tp 寄存器 (1094)。在准备返回用户空间时，prepare_return 将 tp 保存在 trampoline 页中，以防用户代码修改它。最后，当从用户空间进入内核时，uservec 会恢复保存的 tp (3127)。编译器保证绝不会在内核代码中修改 tp。如果 xv6 能够在需要时随时向 RISC-V 硬件查询当前的 hartid 会更方便，但 RISC-V 仅允许在机器模式下这样做，而不允许在监管者模式（supervisor mode）下这样做。

The return values of cpuid and mycpu are fragile: if the timer were to interrupt and cause the thread to yield and later resume execution on a different CPU, a previously returned value would no longer be correct. To avoid this problem, xv6 requires code to disable interrupts before calling cpuid() or mycpu(), and only enable interrupts when done using the returned value.

cpuid 和 mycpu 的返回值是脆弱的：如果定时器中断发生并导致线程让出 CPU，随后在另一个不同的 CPU 上恢复执行，那么之前返回的值将不再正确。为了避免这个问题，xv6 要求代码在调用 cpuid() 或 mycpu() 之前禁用中断，并且只有在使用完返回值后才开启中断。

The function myproc (2187) returns the struct proc pointer for the process that is running on the current CPU. myproc disables interrupts, invokes mycpu, fetches the current process pointer (c->proc) out of the struct cpu, and then enables interrupts. The return value of myproc is safe to use even if interrupts are enabled: if a timer interrupt moves the calling process to a different CPU, its struct proc pointer will stay the same.

函数 myproc (2187) 返回当前 CPU 上运行进程的 struct proc 指针。myproc 禁用中断，调用 mycpu，从 struct cpu 中获取当前进程指针 (c->proc)，然后开启中断。即使在开启中断的情况下，myproc 的返回值也可以安全使用：如果定时器中断将调用进程移动到另一个 CPU，其 struct proc 指针仍将保持不变。

## 8.6 Real world

The xv6 scheduler implements a simple scheduling policy that runs each process in turn. This policy is called round robin. Real operating systems implement more sophisticated policies that, for example, allow processes to have priorities. The idea is that a runnable high-priority process will be preferred by the scheduler over a runnable low-priority process. These policies can become complex because there are often competing goals: for example, the operating system might also want to guarantee fairness and high throughput.

xv6 调度器实现了一种简单的调度策略，即轮流运行每个进程。这种策略被称为轮询调度（round robin）。真实的操作系统会实现更复杂的策略，例如，允许进程拥有优先级。其核心思想是，调度器会优先选择可运行的高优先级进程，而非可运行的低优先级进程。这些策略可能会变得非常复杂，因为往往存在相互竞争的目标：例如，操作系统可能还希望保证公平性和高吞吐量。

## 8.7 Exercises

1. Modify xv6 to use only one context switch when switching from one process’s kernel thread to another, rather than switching through the scheduler thread. The yielding thread will need to select the next thread itself and call swtch. The challenges will be to prevent multiple CPUs from executing the same thread accidentally; to get the locking right; and to avoid deadlocks.
   修改 xv6，使其在从一个进程的内核线程切换到另一个进程时，仅使用一次上下文切换，而不是通过调度器线程进行中转。让出 CPU 的线程需要自行选择下一个线程并调用 swtch。其中的挑战在于：防止多个 CPU 意外执行同一个线程；确保锁的使用正确；以及避免死锁。

