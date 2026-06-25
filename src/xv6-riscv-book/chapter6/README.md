---
title: xv6 riscv book chapter 6：Interrupts and device drivers
date: 2025-07-27
tag: 
- OS
- risc-v
category: 
- OS
- risc-v
---

# xv6 riscv book chapter 6：Interrupts and device drivers

A driver is the code in an operating system that manages a particular device: it configures the device hardware, tells the device to perform operations, handles the resulting interrupts, and interacts with processes using the device. Driver code can be tricky because a driver executes concurrently with the device, and often concurrently with processes using the device. In addition, the driver must understand the device’s hardware interface, which can be complex and poorly documented.

驱动程序是操作系统中用于管理特定设备的硬件代码：它负责配置设备硬件、指示设备执行操作、处理产生的中断，并与使用该设备的进程进行交互。编写驱动程序代码可能非常棘手，因为驱动程序与设备是并发执行的，且通常也与使用该设备的进程并发执行。此外，驱动程序必须理解设备的硬件接口，而这些接口往往非常复杂且缺乏完善的文档。

Devices that need attention from the operating system can usually be configured to generate interrupts, which are one type of trap. The kernel trap handling code recognizes when a device has raised an interrupt and calls the driver’s interrupt handler; in xv6, this dispatch happens in devintr (3506).

需要操作系统关注的设备通常可以被配置为产生中断，中断是陷阱（trap）的一种。内核陷阱处理代码会识别设备何时发出了中断，并调用驱动程序的中断处理程序；在 xv6 中，这种分发过程发生在 devintr (3506) 中。

Many device drivers execute code in two contexts: a top half that runs in a process’s kernel thread, and a bottom half that executes at interrupt time. The top half is called via system calls such as read and write that want the device to perform I/O. This code may ask the hardware to start an operation (e.g., ask the disk to read a block); then the code waits for the operation to complete. Eventually the device completes the operation and raises an interrupt. The driver’s interrupt handler, acting as the bottom half, figures out what operation has completed, wakes up a waiting process if appropriate, and tells the hardware to start work on the next operation, if any.

许多设备驱动程序在两种上下文中执行代码：上半部分（top half）运行在进程的内核线程中，下半部分（bottom half）则在中断发生时执行。上半部分通过 read 和 write 等系统调用被调用，这些调用要求设备执行 I/O 操作。这段代码可能会要求硬件开始一项操作（例如，要求磁盘读取一个块）；然后代码会等待操作完成。最终，设备完成操作并发出中断。驱动程序的中断处理程序作为下半部分，负责查明哪项操作已完成，并在适当时唤醒等待的进程，同时指示硬件开始执行下一项操作（如果有）。

## 6.1 Code: Console input

The console driver (6950) is a simple illustration of driver structure. The console driver accepts characters typed by a human, via the UART serial-port hardware attached to the RISC-V. The console driver accumulates a line of input at a time, processing special input characters such as backspace and control-u. User processes, such as the shell, use the read system call to fetch lines of input from the console. When you type input to xv6 in QEMU, your keystrokes are delivered to xv6 by way of QEMU’s simulated UART hardware.

控制台驱动程序 (6950) 是驱动程序结构的简单示例。控制台驱动程序通过连接到 RISC-V 的 UART 串口硬件接收人类输入的字符。控制台驱动程序一次累积一行输入，并处理退格键和 control-u 等特殊输入字符。用户进程（如 shell）使用 read 系统调用从控制台获取输入行。当你在 QEMU 中向 xv6 输入内容时，你的按键会通过 QEMU 模拟的 UART 硬件传递给 xv6。

The UART hardware that the driver talks to is a 16550 chip [13] emulated by QEMU. On a real computer, a 16550 would manage an RS232 serial link connecting to a terminal or other computer. When running QEMU, it’s connected to your keyboard and display.

驱动程序与之通信的 UART 硬件是 QEMU 模拟的 16550 芯片 [13]。在真实的计算机上，16550 会管理连接到终端或其他计算机的 RS232 串口链路。在运行 QEMU 时，它连接到你的键盘和显示器。

The UART hardware appears to software as a set of memory-mapped control registers. That is, there are some physical addresses that are connected to the UART device, so that loads and stores interact with the device hardware rather than RAM. The memory-mapped addresses for the UART start at 0x10000000, or UART0 (0220). There are a handful of UART control registers, each the width of a byte. Their offsets from UART0 are defined in (7221). For example, the LSR register contains bits that indicate whether input characters are waiting to be read by the driver. These characters (if any) are available for reading from the RHR register. Each time one is read, the UART hardware deletes it from an internal FIFO of waiting characters, and clears the “ready” bit in LSR when the FIFO is empty. To transmit, the driver writes a byte to the THR register, which causes the UART to append the byte to a FIFO of bytes that the UART will send on the RS232 serial link. The UART transmit and receive hardware are largely independent of each other.

UART 硬件在软件看来是一组内存映射的控制寄存器。这些也就是说，有一些物理地址连接到了 UART 设备，因此加载（load）和存储（store）指令是与设备硬件交互，而不是与 RAM 交互。UART 的内存映射地址起始于 0x10000000，即 UART0 (0220)。UART 有若干个控制寄存器，每个寄存器的宽度为一个字节。它们相对于 UART0 的偏移量定义在 (7221) 中。例如，LSR 寄存器包含指示输入字符是否正等待驱动程序读取的位。这些字符（如果有）可以从 RHR 寄存器中读取。每读取一个字符，UART 硬件就会将其从内部的等待字符 FIFO（先进先出队列）中删除，并在 FIFO 为空时清除 LSR 中的“就绪”位。为了发送数据，驱动程序向 THR 寄存器写入一个字节，这会使 UART 将该字节追加到发送 FIFO 中，随后 UART 会将其通过 RS232 串口链路发送。UART 的发送和接收硬件在很大程度上是相互独立的。

Xv6’s main calls consoleinit (7154) to initialize the UART hardware. This code configures the UART to generate a receive interrupt when the UART receives each byte of input, and a transmit complete interrupt each time the UART finishes sending a byte of output (7251).

Xv6 的 main 函数调用 consoleinit (7154) 来初始化 UART 硬件。这段代码将 UART 配置为：每当 UART 接收到一个字节的输入时，产生一个接收中断；每当 UART 完成发送一个字节的输出时，产生一个发送完成中断 (7251)。

The xv6 shell reads from the console by way of a file descriptor opened by init.c (7768). Calls to the read system call make their way through the kernel to consoleread (7040). consoleread waits for input to arrive (via interrupts) and be buffered in cons.buf, copies the input to user space, and (after a whole line has arrived) returns to the user process. If the user hasn’t typed a full line yet, any reading processes will wait in the sleep call (7056) (Chapter 9 explains the details of sleep).

Xv6 的 shell 通过 init.c (7768) 打开的文件描述符从控制台读取数据。对 read 系统调用的调用会通过内核传递到 consoleread (7040)。consoleread 等待输入到达（通过中断）并缓冲在 cons.buf 中，将输入复制到用户空间，并在（整行到达后）返回给用户进程。如果用户尚未输入完整的一行，任何读取进程都将在 sleep 调用 (7056) 中等待（第 9 章解释了 sleep 的细节）。

When the user types a character, the UART hardware asks the RISC-V to raise an interrupt, which activates xv6’s trap handler. The trap handler calls devintr (3506), which looks at the RISC-V scause register to discover that the interrupt is from an external device. Then it asks a hardware unit called the PLIC [3] to tell it which device interrupted (3514). If it was the UART, devintr calls uartintr. uartintr (7354) reads any waiting input characters from the UART hardware and hands them to consoleintr (7107); it doesn’t wait for characters, since future input will raise a new interrupt. The job of consoleintr is to accumulate input characters in cons.buf until a whole line arrives. consoleintr treats backspace and a few other characters specially. When a newline arrives, consoleintr wakes up a waiting consoleread (if there is one).

当用户输入一个字符时，UART 硬件会请求 RISC-V 触发一个中断，从而激活 xv6 的陷阱处理程序（trap handler）。陷阱处理程序调用 devintr (3506)，后者通过查看 RISC-V 的 scause 寄存器发现该中断来自外部设备。然后，它请求一个名为 PLIC [3] 的硬件单元告知是哪个设备触发了中断 (3514)。如果是 UART，devintr 就会调用 uartintr。`uartintr` (7354) 从 UART 硬件读取任何等待中的输入字符，并将其交给 `consoleintr` (7107)；它不会等待字符，因为未来的输入会触发新的中断。`consoleintr` 的任务是将输入字符累积在 `cons.buf` 中，直到整行输入到达。`consoleintr` 会对退格键和其他一些特殊字符进行处理。当换行符到达时，`consoleintr` 会唤醒正在等待的 `consoleread`（如果存在的话）。

Once woken, consoleread will observe a full line in cons.buf, copy it to user space, and return (via the system call machinery) to user space.

一旦被唤醒，`consoleread` 将在 `cons.buf` 中看到完整的一行，将其复制到用户空间，并（通过系统调用机制）返回到用户空间。

## 6.2 Code: Console output

A write system call on a file descriptor connected to the console eventually arrives at uartputc (7309). The device driver maintains an output buffer (uart_tx_buf) so that writing processes do not have to wait for the UART to finish sending; instead, uartputc appends each character to the buffer, calls uartstart to start the device transmitting (if it isn’t already), and returns. The only situation in which uartputc waits is if the buffer is already full.

对连接到控制台的文件描述符进行 `write` 系统调用，最终会到达 `uartputc` (7309)。设备驱动程序维护着一个输出缓冲区（`uart_tx_buf`），这样写入进程就不必等待 UART 完成发送；相反，`uartputc` 将每个字符追加到缓冲区，调用 `uartstart` 启动设备传输（如果尚未启动），然后返回。`uartputc` 唯一需要等待的情况是缓冲区已满。

Each time the UART finishes sending a byte, it generates an interrupt. uartintr calls uartstart, which checks that the device really has finished sending, and hands the device the next buffered output character. Thus if a process writes multiple bytes to the console, typically the first byte will be sent by uartputc’s call to uartstart, and the remaining buffered bytes will be sent by uartstart calls from uartintr as transmit complete interrupts arrive.

每当 UART 完成一个字节的发送，它就会产生一个中断。uartintr 会调用 uartstart，后者检查设备是否确实已完成发送，并将缓冲区中的下一个输出字符交给设备。因此，如果一个进程向控制台写入多个字节，通常第一个字节将第一个字节将由 `uartputc` 调用 `uartstart` 发送，而剩余的缓冲字节将随着传输完成中断的到来，由 `uartintr` 调用的 `uartstart` 发送。

A general pattern to note is the decoupling of device activity from process activity via buffering and interrupts. The console driver can process input even when no process is waiting to read it; a subsequent read will see the input. Similarly, processes can send output without having to wait for the device. This decoupling can increase performance by allowing processes to execute concurrently with device I/O, and is particularly important when the device is slow (as with the UART) or needs immediate attention (as with echoing typed characters). This idea is sometimes called concurrency.

值得注意的一个通用模式是，通过缓冲和中断实现了设备活动与进程活动的解耦。即使没有进程等待读取，控制台驱动程序也能处理输入；随后的读取操作将能看到这些输入。同样，进程可以发送输出而无需等待设备。这种解耦通过允许进程与设备 I/O 并发执行来提高性能，当设备速度较慢（如 UART）或需要立即响应（如回显键入的字符）时，这一点尤为重要。这种思想有时被称为 并发。

## 6.3 Concurrency in drivers

You may have noticed calls to acquire in consoleread and in consoleintr. These calls acquire a lock, which protects the console driver’s data structures from concurrent access. There are three concurrency dangers here: two processes on different CPUs might call consoleread at the same time; the hardware might ask a CPU to deliver a console (really UART) interrupt while that CPU is already executing inside consoleread; and the hardware might deliver a console interrupt on a different CPU while consoleread is executing. Chapter 7 explains how to use locks to ensure that these dangers don’t lead to incorrect results.

你可能已经注意到在 consoleread 和 consoleintr 中调用了 acquire。这些调用获取了一个锁，用于保护控制台驱动程序的数据结构免受并发访问。这里存在三种并发风险：运行在不同 CPU 上的两个进程可能同时调用 consoleread；硬件可能在某个 CPU 正在执行 consoleread 时，请求该 CPU 传递控制台（实际上是 UART）中断；硬件也可能在 consoleread 执行期间，在另一个不同的 CPU 上传递控制台中断。第 7 章将解释如何使用锁来确保这些风险不会导致错误的结果。

Another way in which concurrency requires care in drivers is that one process may be waiting for input from a device, but the interrupt signaling arrival of the input may arrive when a different process (or no process at all) is running. Thus interrupt handlers are not allowed to think about the process or code that they have interrupted. For example, an interrupt handler cannot safely call copyout with the current process’s page table. Interrupt handlers typically do relatively little work (e.g., just copy the input data to a buffer), and wake up top-half code to do the rest.

驱动程序中需要谨慎处理并发的另一种情况是：一个进程可能正在等待来自设备的输入，但信号通知输入到达的中断可能在另一个进程（或根本没有进程）运行时到达。因此，中断处理程序不允许考虑它们所中断的进程或代码。例如，中断处理程序不能安全地使用当前进程的页表调用 copyout。中断处理程序通常只做相对较少的工作（例如，仅将输入数据复制到缓冲区），然后唤醒上半部分（top-half）代码来完成剩余工作。

## 6.4 Timer interrupts

Xv6 uses timer interrupts to maintain its idea of the current time and to switch among computebound processes. Timer interrupts come from clock hardware attached to each RISC-V CPU. Xv6 programs each CPU’s clock hardware to interrupt the CPU periodically.

Xv6 使用定时器中断来维护其当前时间的概念，并在计算密集型进程之间进行切换。定时器中断来自连接到每个 RISC-V CPU 的时钟硬件。Xv6 对每个 CPU 的时钟硬件进行编程，使其定期中断 CPU。

Code in start.c(1102) sets some control bits that allow supervisor-mode access to the timer control registers, and then asks for the first timer interrupt. The time control register contains a count that the hardware increments at a steady rate; this serves as a notion of the current time. The stimecmp register contains a time at which the the CPU will raise a timer interrupt; setting st ime cmp to the current value of time plus will schedule an interrupt time units in the future. For qemu’s RISC-V emulation, 1000000 time units is roughly a tenth of second.

start.c(1102) 中的代码设置了一些控制位，允许监管者模式（supervisor-mode）访问定时器控制寄存器，然后请求第一次定时器中断。time 控制寄存器包含一个由硬件以稳定速率递增的计数；这充当了当前时间的概念。stimecmp 寄存器包含一个 CPU 将触发定时器中断的时间点；将 stimecmp 设置为 time 的当前值加上 ，将调度一个在未来 个时间单位发生的中断。对于 qemu 的 RISC-V 模拟，1,000,000 个时间单位大约是十分之一秒。

Timer interrupts arrive via usertrap or kerneltrap and devintr, like other device interrupts. Timer interrupts arrive with scause’s low bits set to five; devintr in trap. c detects this situation and calls clockintr (3482). The latter function increments ticks, allowing the kernel to track the passage of time. The increment occurs on only one CPU, to avoid time passing faster if there are multiple CPUs. clockintr wakes up any processes waiting in the pause system call, and schedules the next timer interrupt by writing stimecmp. devintr return 2 for a timer interrupt in order to indicate to kerneltrap or usertrap that they should call yield so that CPUs can be multiplexed among runnable processes.

与其他设备中断一样，定时器中断通过 usertrap 或 kerneltrap 以及 devintr 到达。定时器中断到达时，scause 的低位被设置为 5；trap.c 中的 devintr 会检测到这种情况并调用 clockintr (3482)。后一个函数会递增 ticks，从而允许内核跟踪时间的流逝。递增操作仅在单个 CPU 上发生，以避免在存在多个 CPU 时时间流逝得更快。clockintr 会唤醒所有在 pause 系统调用中等待的进程，并通过写入 stimecmp 来调度下一次定时器中断。对于定时器中断，devintr 返回 2，以便向 kerneltrap 或 usertrap 指示它们应该调用 yield，从而使 CPU 可以在可运行进程之间进行多路复用。

The fact that kernel code can be interrupted by a timer interrupt that forces a context switch via yield is part of the reason why early code in usertrap is careful to save state such as sepc before enabling interrupts. These context switches also mean that kernel code must be written in the knowledge that it may move from one CPU to another without warning.

内核代码可能被定时器中断打断，并通过 yield 强制进行上下文切换，这也是为什么 usertrap 中的早期代码在开启中断之前，必须谨慎地保存 sepc 等状态的原因之一。这些上下文切换还意味着，编写内核代码时必须意识到，它可能会在毫无预警的情况下从一个 CPU 迁移到另一个 CPU。

## 6.5 Real world

Xv6, like many operating systems, allows interrupts and even context switches (via yield) while executing in the kernel. The reason for this is to retain quick response times during complex system calls that run for a long time. However, as noted above, allowing interrupts in the kernel is the source of some complexity; as a result, a few operating systems allow interrupts only while executing user code.

与许多操作系统一样，xv6 允许在内核执行期间发生中断甚至上下文切换（通过 yield）。这样做的目的是为了在执行耗时较长的复杂系统调用时，仍能保持快速的响应时间。然而，如上所述，允许内核中断是某些复杂性的根源；因此，少数操作系统仅在执行用户代码时才允许中断。

Supporting all the devices on a typical computer in its full glory is much work, because there are many devices, the devices have many features, and the protocol between device and driver can be complex and poorly documented. In many operating systems, the drivers account for more code than the core kernel.

要全面支持典型计算机上的所有设备是一项巨大的工程，因为设备种类繁多，功能各异，且设备与驱动程序之间的协议可能非常复杂且缺乏文档。在许多操作系统中，驱动程序的代码量甚至超过了内核核心代码。

The UART driver retrieves data a byte at a time by reading the UART control registers; this pattern is called programmed , since software is driving the data movement. Programmed I/O is simple, but too slow to be used at high data rates. Devices that need to move lots of data at high speed typically use direct memory access (DMA). DMA device hardware directly writes incoming data to RAM, and reads outgoing data from RAM. Modern disk and network devices use DMA. A driver for a DMA device would prepare data in RAM, and then use a single write to a control register to tell the device to process the prepared data.

UART 驱动程序通过读取 UART 控制寄存器，一次检索一个字节的数据；这种模式被称为程序控制 （programmed I/O），因为是由软件驱动数据传输。程序控制 I/O 虽然简单，但对于高速率的数据传输来说太慢了。需要高速传输大量数据的设备通常使用直接内存访问（DMA）。DMA 设备硬件直接将输入数据写入 RAM，并从 RAM 中读取输出数据。现代磁盘和网络设备都使用 DMA。DMA 设备的驱动程序会在 RAM 中准备好数据，然后通过对控制寄存器的一次写入操作，通知设备处理这些准备好的数据。

Interrupts make sense when a device needs attention at unpredictable times, and not too often. But interrupts have high CPU overhead. Thus high speed devices, such as network and disk controllers, use tricks that reduce the need for interrupts. One trick is to raise a single interrupt for a whole batch of incoming or outgoing requests. Another trick is for the driver to disable interrupts entirely, and to check the device periodically to see if it needs attention. This technique is called polling. Polling makes sense if the device performs operations at a high rate, but it wastes CPU time if the device is mostly idle. Some drivers dynamically switch between polling and interrupts depending on the current device load.

当设备在不可预测的时间需要处理，且频率不是太高时，使用中断是有意义的。但中断具有很高的 CPU 开销。因此，高速设备（如网络和磁盘控制器）会使用一些技巧来减少对中断的需求。一种技巧是为一整批进入或发出的请求仅触发一次中断。另一种技巧是让驱动程序完全禁用中断，并定期检查设备以查看其是否需要处理。这种技术被称为轮询（polling）。如果设备以很高的速率执行操作，轮询是有意义的；但如果设备大部分时间处于空闲状态，轮询就会浪费 CPU 时间。一些驱动程序会根据当前的设备负载，在轮询和中断之间动态切换。

The UART driver copies incoming data first to a buffer in the kernel, and then to user space. This makes sense at low data rates, but such a double copy can significantly reduce performance for devices that generate or consume data very quickly. Some operating systems are able to directly move data between user-space buffers and device hardware, often with DMA.

UART 驱动程序首先将输入数据复制到内核缓冲区，然后再复制到用户空间。在低数据速率下这样做是有意义的，但对于产生或消耗数据非常快的设备，这种双重复制会显著降低性能。一些操作系统能够直接在用户空间缓冲区和设备硬件之间移动数据，通常是利用 DMA 技术。

As mentioned in Chapter 1, the console appears to applications as a regular file, and applications read input and write output using the read and write system calls. Applications may want to control aspects of a device that cannot be expressed through the standard file system calls (e.g., enabling/disabling line buffering in the console driver). Unix operating systems provide an ioctl system call for such cases.

正如第 1 章所述，控制台在应用程序看来就像一个普通文件，应用程序使用 read 和 write 系统调用来读取输入和写入输出。应用程序可能希望控制设备的某些方面，而这些方面无法通过标准的文件系统调用来表达（例如：（例如：在控制台驱动程序中启用/禁用行缓冲）。Unix 操作系统为此类情况提供了一个 ioctl 系统调用。

Some uses of computers require “real-time” responses to external events: responses guaranteed to occur within a bounded time. For example, in safety-critical systems missing a deadline can lead to disasters. Xv6 is not suitable for real-time settings. Among other things, xv6’s scheduler does not take into account real-time deadlines when it decides what process to run next, and xv6 has long kernel code paths with interrupts disabled, so that it may not respond to interrupts quickly. A real-time operating system must not only fix these problems, but also be structured in a way that allows analysis of worst-case response times.

计算机的一些用途需要对外部事件做出“实时”响应：即保证在限定时间内发生的响应。例如，在安全至关重要的系统中，错过截止时间可能会导致灾难。Xv6 不适用于实时环境。除此之外，xv6 的调度程序在决定下一个运行哪个进程时不会考虑实时截止时间，而且 xv6 拥有很长的禁用中断的内核代码路径，因此它可能无法快速响应中断。实时操作系统不仅必须解决这些问题，还必须以一种能够分析最坏情况响应时间的方式进行构建。

## 6.6 Exercises

1. Modify uart. c to not use interrupts at all. You may need to modify console. c as well.
   修改 uart.c 以完全不使用中断。你可能还需要修改 console.c。
2. Add a driver for an Ethernet card.
   为以太网卡添加驱动程序。

