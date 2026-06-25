---
title: xv6 riscv book chapter 1：Operating system interfaces
date: 2025-07-27
tag: 
- OS
- risc-v
category: 
- OS
- risc-v
---

# xv6 riscv book chapter 1：Operating system interfaces

The job of an operating system is to share a computer among multiple programs and to provide a more useful set of services than the hardware alone supports. An operating system manages and abstracts the low-level hardware, so that, for example, a word processor need not concern itself with which type of disk hardware is being used. An operating system shares the hardware among multiple programs so that they run (or appear to run) at the same time. Finally, operating systems provide controlled ways for programs to interact, so that they can share data or work together.

操作系统的职责是在多个程序之间共享计算机，并提供比硬件本身支持的功能更实用的服务。操作系统管理并抽象底层硬件，例如，文字处理器无需关心正在使用的是哪种类型的磁盘硬件。操作系统在多个程序之间共享硬件，使它们能够同时运行（或看起来在同时运行）。最后，操作系统为程序交互提供受控的方式，以便它们可以共享数据或协同工作。

An operating system provides services to user programs through an interface. Designing a good interface turns out to be difficult. On the one hand, we would like the interface to be simple and narrow because that makes it easier to get the implementation right. On the other hand, we may be tempted to offer many sophisticated features to applications. The trick in resolving this tension is to design interfaces that rely on a few mechanisms that can be combined to provide much generality.

操作系统通过接口向用户程序提供服务。设计一个好的接口被证明是困难的。一方面，我们希望接口简单且狭窄，因为这更容易确保实现的正确性。另一方面，我们可能会倾向于为应用程序提供许多复杂的功能。解决这种矛盾的诀窍是设计依赖于少数机制的接口，通过这些机制的组合来提供极大的通用性。

This book uses a single operating system as a concrete example to illustrate operating system concepts. That operating system, xv6, provides the basic interfaces introduced by Ken Thompson and Dennis Ritchie’s Unix operating system [17], as well as mimicking Unix’s internal design. Unix provides a narrow interface whose mechanisms combine well, offering a surprising degree of generality. This interface has been so successful that modern operating systems-BSD, Linux, macOS, Solaris, and even, to a lesser extent, Microsoft Windows-have Unix-like interfaces. Understanding xv6 is a good start toward understanding any of these systems and many others.

本书以一个具体的操作系统为例来阐述操作系统的概念。这个名为 xv6 的操作系统提供了由 Ken Thompson 和 Dennis Ritchie 的 Unix 操作系统 [17] 所引入的基础接口，并模仿了 Unix 的内部设计。Unix 提供了一个紧凑的接口，其各项机制能够很好地结合，从而提供了惊人的通用性。这一接口非常成功，以至于现代操作系统——BSD、Linux、macOS、Solaris，甚至在较小程度上的 Microsoft Windows——都拥有类 Unix 接口。理解 xv6 是理解这些系统以及许多其他系统的良好开端。

As Figure 1.1 shows, xv6 takes the traditional form of a kernel, a special program that provides services to running programs. Each running program, called a process, has memory containing instructions, data, and a stack. The instructions implement the program’s computation. The data are the variables on which the computation acts. The stack organizes the program’s procedure calls. A given computer typically has many processes but only a single kernel.

如图 1.1 所示，xv6 采用了传统的内核形式，内核是一个为运行中的程序提供服务的特殊程序。每个运行中的程序被称为进程，它拥有包含指令、数据和栈的内存。指令实现程序的计算；数据是计算所作用的变量；栈则组织程序的函数调用。一台给定的计算机通常有许多个进程，但只有一个内核。

When a process needs to invoke a kernel service, it invokes a system call, one of the calls in the operating system’s interface. The system call enters the kernel; the kernel performs the service and returns. Thus a process alternates between executing in user space and kernel space.

当进程需要调用内核服务时，它会发起系统调用，这是操作系统接口中的一种调用。系统调用进入内核；内核执行服务并返回。因此，进程在用户空间和内核空间的执行之间交替切换。

As described in detail in subsequent chapters, the kernel uses the hardware protection mechanisms provided by a CPU to ensure that each process executing in user space can access only

正如后续章节详细描述的那样，内核利用 CPU 提供的硬件保护机制，确保每个在用户空间执行的进程只能访问


its own memory. The kernel executes with the hardware privileges required to implement these protections; user programs execute without those privileges. When a user program invokes a system call, the hardware raises the privilege level and starts executing a pre-arranged function in the kernel.

内核拥有自己的内存。内核在执行时具有实现这些保护机制所需的硬件特权；而用户程序在执行时不具备这些特权。当用户程序调用系统调用时，硬件会提升特权级别，并开始执行内核中预先安排好的函数。

The collection of system calls that a kernel provides is the interface that user programs see. The xv6 kernel provides a subset of the services and system calls that Unix kernels traditionally offer. Figure 1.2 lists all of xv6’s system calls.

内核提供的系统调用集合是用户程序所能看到的接口。xv6 内核提供了传统 Unix 内核所提供的服务和系统调用的一个子集。图 1.2 列出了 xv6 的所有系统调用。

The rest of this chapter outlines xv6’s services-processes, memory, file descriptors, pipes, and a file system—and illustrates them with code snippets and discussions of how the shell, Unix’s command-line user interface, uses them. The shell’s use of system calls illustrates how carefully they have been designed.

本章接下来的部分将概述 xv6 的服务——进程、内存、文件描述符、管道和文件系统，并通过代码片段以及对 Shell（Unix 的命令行用户界面）如何使用这些服务的讨论来进行说明。Shell 对系统调用的使用展示了这些接口设计的精妙之处。

The shell is an ordinary program that reads commands from the user and executes them. The fact that the shell is a user program, and not part of the kernel, illustrates the power of the system call interface: there is nothing special about the shell. It also means that the shell is easy to replace; as a result, modern Unix systems have a variety of shells to choose from, each with its own user interface and scripting features. The xv6 shell is a simple implementation of the essence of the Unix Bourne shell.

Shell 是一个普通的程序，它读取用户的命令并执行它们。Shell 是一个用户程序而非内核的一部分，这一事实说明了系统调用接口的强大：Shell 并没有什么特殊之处。这也意味着 Shell 很容易被替换；因此，现代 Unix 系统有多种 Shell 可供选择，每种都有其独特的用户界面和脚本功能。xv6 的 Shell 是对 Unix Bourne Shell 精髓的一个简单实现。

The implementation of the xv6 shell can be found at (7850). (The link is a hyperlink to the relevant xv6 source code at https://github.com/mit-pdos/xv6-riscv/ and the specific number refers to the sheet and line number in xv6-src-booklet.pdf, as in the Lions’ Commentary on UNIX 6th Edition [11]. A good practice is to try to read the source code first on your own (in your favorite development environment, on github, or in a PDF viewer) and then come back to this book. By the end of this book you should be able to understand every line of xv6 source code without having to consult this book.

xv6 shell 的实现可以在 (7850) 处找到。（该链接是指向 https://github.com/mit-pdos/xv6-riscv/ 上相关 xv6 源代码的超链接，具体的数字指的是 xv6-src-booklet.pdf 中的页码和行号，类似于《Lions' Commentary on UNIX 6th Edition》[11] 中的做法。一个好的实践是尝试先自己阅读源代码（在你喜欢的开发环境、GitHub 或 PDF 查看器中），然后再回到本书。在读完本书时，你应该能够在无需查阅本书的情况下理解 xv6 源代码的每一行。

## 1.1 Processes and memory

An xv6 process consists of user-space memory (instructions, data, and stack) and per-process state private to the kernel. Xv6 time-shares processes: it transparently switches the available CPUs among the set of processes waiting to execute. When a process is not executing, xv6 saves the process’s CPU registers, restoring them when it next runs the process. The kernel associates a

一个 xv6 进程由用户空间内存（指令、数据和栈）以及内核私有的逐进程状态组成。Xv6 对进程进行分时复用：它在等待执行的进程集之间透明地切换可用 CPU。当一个进程不在执行时，xv6 会保存该进程的 CPU 寄存器，并在下次运行该进程时将其恢复。内核为每个进程关联一个


process identifier, or PID, with each process. A process may create a new process using the fork system call. fork gives the new process an exact copy of the calling process’s memory: fork copies the instructions, data, and stack of the calling process into the new process’s memory. fork returns in both the original and new processes. In the original process, fork returns the new process’s PID. In the new process, fork returns zero. The original and new processes are often called the parent and child.

每个进程都有一个进程标识符，即 PID。进程可以使用 fork 系统调用创建一个新进程。fork 为新进程提供一份调用进程内存的精确副本：fork 将调用进程的指令、数据和栈复制到新进程的内存中。fork 在原进程和新进程中都会返回。在原进程中，fork 返回新进程的 PID。在新进程中，fork 返回零。原进程和新进程通常被称为父进程和子进程。

For example, consider the following program fragment written in the C programming language [7]:

例如，考虑以下用 C 语言编写的程序片段 [7]：

```c
int pid = fork();
if(pid > 0) {
    printf("parent: child=%d\n", pid);
    pid = wait((int *) 0);
    printf("child %d is done\n", pid);
} else if(pid == 0){
    printf("child: exiting\n");
    exit(0);
} else {
    printf("fork error\n");
}
```

The exit system call causes the calling process to stop executing and to release resources such as memory and open files. Exit takes an integer status argument, conventionally 0 to indicate success and 1 to indicate failure. The wait system call returns the PID of an exited (or killed) child of the current process and copies the exit status of the child to the address passed to wait; if none of the caller’s children has exited, wait waits for one to do so. If the caller has no children, wait immediately returns -1 . If the parent doesn’t care about the exit status of a child, it can pass a 0 address to wait.

exit 系统调用导致调用进程停止执行，并释放内存和打开的文件等资源。exit 接受一个整数状态参数，按惯例 0 表示成功，1 表示失败。wait 系统调用返回当前进程中已退出（或被杀死）的子进程的 PID，并将该子进程的退出状态复制到传递给 wait 的地址中；如果调用者的子进程都没有退出，wait 会等待其中一个退出。如果调用者没有子进程，wait 立即返回 -1。如果父进程不关心子进程的退出状态，可以向 wait 传递一个 0 地址。

In the example, the output lines

在示例中，输出行

```c
parent: child=1234
child: exiting
```

might come out in either order (or even intermixed), depending on whether the parent or child gets to its printf call first. After the child exits, the parent’s wait returns, causing the parent to print

可能会以任意顺序出现（甚至交织在一起），这取决于父进程还是子进程先执行到 printf 调用。子进程退出后，父进程的 wait 调用返回，使得父进程打印出

```c
parent: child 1234 is done
```

Although the child starts with a copy of the parent’s memory, the parent and child execute with separate memory and separate registers: changing a variable in one does not affect the other. For example, when the return value of wait is stored into pid in the parent process, it doesn’t change the variable pid in the child. The value of pid in the child will still be zero.

虽然子进程起初拥有父进程内存的副本，但父进程和子进程是在独立的内存和独立的寄存器中执行的：在其中一个进程中修改变量不会影响另一个。例如，当 wait 的返回值在父进程中存入 pid 时，它并不会改变子进程中的变量 pid。子进程中的 pid 值仍将为零。

The exec system call replaces the calling process’s memory with a new memory image loaded from a file stored in the file system. The file must have a particular format, which specifies which part of the file holds instructions, which part is data, at which instruction to start, etc. Xv6 uses the ELF format, which Chapter 3 discusses in more detail. Usually the file is the result of compiling a program’s source code. When exec succeeds, it does not return to the calling program; instead, the instructions loaded from the file start executing at the entry point declared in the ELF header. exec takes two arguments: the name of the file containing the executable and an array of string arguments. For example:

exec 系统调用会用从文件系统中加载的新内存镜像替换调用进程的内存。该文件必须具有特定的格式，用以指定文件的哪一部分存放指令、哪一部分是数据、从哪条指令开始执行等等。Xv6 使用 ELF 格式，第 3 章将对此进行更详细的讨论。通常，该文件是编译程序源代码的结果。当 exec 成功执行时，它不会返回到调用程序；相反，从文件中加载的指令将从 ELF 头部声明的入口点开始执行。exec 接收两个参数：包含可执行文件的文件名和一个字符串参数数组。例如：

```c
char *argv[3];
argv[0] = "echo";
argv[1] = "hello";
argv[2] = 0;
exec("/bin/echo", argv);
printf("exec error\n");
```

This fragment replaces the calling program with an instance of the program /bin/echo running with the argument list echo hello. Most programs ignore the first element of the argument array, which is conventionally the name of the program.

这段代码片段将调用程序替换为 /bin/echo 程序的一个实例，并带有参数列表 echo hello。大多数程序会忽略参数数组的第一个元素，按照惯例，该元素是程序的名称。

The xv6 shell uses the above calls to run programs on behalf of users. The main structure of the shell is simple; see main (8001). The main loop reads a line of input from the user with getcmd. Then it calls fork, which creates a copy of the shell process. The parent calls wait, while the child runs the command. For example, if the user had typed “echo hello” to the shell, runcmd would have been called with “echo hello” as the argument. runcmd (7903) runs the actual command. For “echo hello”, it would call exec (7927). If exec succeeds then the child will execute instructions from echo instead of runcmd. At some point echo will call exit, which will cause the parent to return from wait in main (8001).

xv6 shell 使用上述调用代表用户运行程序。shell 的主要结构很简单；参见 main (8001)。主循环通过 getcmd 从用户那里读取一行输入。然后它调用 fork，创建一个 shell 进程的副本。父进程调用 wait，而子进程运行命令。例如，如果用户向 shell 输入了 “echo hello”，runcmd 将以 “echo hello” 作为参数被调用。runcmd (7903) 运行该实际的命令。对于“echo hello”，它会调用 exec (7927)。如果 exec 成功，子进程将执行来自 echo 的指令，而不是 runcmd。在某个时刻，echo 会调用 exit，这将导致父进程从 main (8001) 中的 wait 返回。

You might wonder why fork and exec are not combined in a single call; we will see later that the shell exploits the separation in its implementation of I/O redirection. To avoid the wastefulness of creating a duplicate process and then immediately replacing it (with exec), operating kernels optimize the implementation of fork for this use case by using virtual memory techniques such as copy-on-write (see Section 5).

你可能会好奇为什么 fork 和 exec 不合并为一个调用；我们稍后会看到，shell 在实现 I/O 重定向时利用了这种分离。为了避免创建一个重复进程然后立即（通过 exec）替换它的浪费，操作系统内核通过使用诸如写时复制（见第 5 节）之类的虚拟内存技术，针对这种用例优化了 fork 的实现。

Xv6 allocates most user-space memory implicitly: fork allocates the memory required for the child’s copy of the parent’s memory, and exec allocates enough memory to hold the executable file. A process that needs more memory at run-time (perhaps for malloc) can call sbrk (n) to grow its data memory by n zero bytes; sbrk returns the location of the new memory.

Xv6 隐式地分配大部分用户空间内存：fork 分配子进程副本所需的父进程内存，而 exec 分配足以容纳可执行文件的内存。在运行时需要更多内存（可能用于 malloc）的进程可以调用 sbrk (n) 来将其数据内存增加 n 个零字节；sbrk 返回新内存的位置。

## 1.2 I/O and File descriptors

A file descriptor is a small integer representing a kernel-managed object that a process may read from or write to. A process may obtain a file descriptor by opening a file, directory, or device, or by creating a pipe, or by duplicating an existing descriptor. For simplicity we’ll often refer to the object a file descriptor refers to as a “file”; the file descriptor interface abstracts away the differences between files, pipes, and devices, making them all look like streams of bytes. We’ll refer to input and output as .

文件描述符是一个小的整数，代表一个由内核管理的、进程可以从中读取或向其写入的对象。进程可以通过打开文件、目录或设备，或者通过创建管道，或者通过复制现有描述符来获得文件描述符。为了简单起见，我们通常将文件描述符所指代的对象称为“文件”；文件描述符接口抽象了文件、管道和设备之间的差异，使它们看起来都像字节流。我们将输入和输出称为 。

Internally, the xv6 kernel uses the file descriptor as an index into a per-process table, so that every process has a private space of file descriptors starting at zero. By convention, a process reads from file descriptor 0 (standard input), writes output to file descriptor 1 (standard output), and writes error messages to file descriptor 2 (standard error). As we will see, the shell exploits the convention to implement I/O redirection and pipelines. The shell ensures that it always has three file descriptors open (8007), which are by default file descriptors for the console.

在内部，xv6 内核将文件描述符作为每个进程表中对应的索引，因此每个进程都有一个从零开始的私有文件描述符空间。按照惯例，进程从文件描述符 0（标准输入）读取，将输出写入文件描述符 1（标准输出），并将错误消息写入文件描述符 2（标准错误）。正如我们将看到的，shell 利用这一惯例来实现 I/O 重定向和管道。shell 确保它始终打开三个文件描述符 (8007)，默认情况下这些是控制台的文件描述符。

The read and write system calls read bytes from and write bytes to open files named by file descriptors. The call read ( , buf, ) reads at most bytes from the file descriptor , copies them into buf, and returns the number of bytes read. Each file descriptor that refers to a file has an offset associated with it. read reads data from the current file offset and then advances that offset by the number of bytes read: a subsequent read will return the bytes following the ones returned by the first read. When there are no more bytes to read, read returns zero to indicate the end of the file.

read 和 write 系统调用通过文件描述符指定的打开文件来读取和写入字节。调用 read ( , buf, ) 从文件描述符 中读取最多 个字节，将其复制到 buf 中，并返回读取的字节数。每个引用文件的文件描述符都有一个与之关联的偏移量。read 从当前文件偏移量处读取数据，然后将该偏移量推进读取的字节数：随后的 read 将返回紧随第一次 read 返回字节之后的内容。当没有更多字节可读时，read 返回零以表示文件结束。

The call write ( fd , buf, n ) writes n bytes from buf to the file descriptor fd and returns the number of bytes written. Fewer than n bytes are written only when an error occurs. Like read, write writes data at the current file offset and then advances that offset by the number of bytes written: each write picks up where the previous one left off.

调用 write ( fd , buf, n ) 将 n 个字节从 buf 写入文件描述符 fd，并返回写入的字节数。只有在发生错误时，写入的字节数才会少于 n。与 read 类似，write 在当前文件偏移量处写入数据，然后将该偏移量推进写入的字节数：每次写入都从上一次写入结束的地方开始。

The following program fragment (which forms the essence of the program cat) copies data from its standard input to its standard output. If an error occurs, it writes a message to the standard error.

以下程序片段（构成了 cat 程序的核心）将数据从其标准输入复制到标准输出。如果发生错误，它会向标准错误写入一条消息。

```c
char buf[512];
int n;
for(;;){
    n = read(0, buf, sizeof buf);
    if(n == 0)
        break;
    if(n < 0) {
        fprintf(2, "read error\n");
        exit(1);
    }
    if(write(1, buf, n) != n) {
        fprintf(2, "write error\n");
        exit(1);
    }
}
```

The important thing to note in the code fragment is that cat doesn’t know whether it is reading from a file, console, or a pipe. Similarly cat doesn’t know whether it is printing to a console, a file, or whatever. The use of file descriptors and the convention that file descriptor 0 is input and file descriptor 1 is output allows a simple implementation of cat.

代码片段中需要注意的重要一点是，cat 并不知晓它是在从文件、控制台还是管道中读取。同样，cat 也不知晓它是在向控制台、文件或其他任何地方打印。文件描述符的使用以及“文件描述符 0 是输入、文件描述符 1 是输出”的惯例，使得 cat 的实现变得非常简单。

The close system call releases a file descriptor, making it free for reuse by a future open, pipe, or dup system call (see below). A newly allocated file descriptor is always the lowestnumbered unused descriptor of the current process.

`close` 系统调用会释放一个文件描述符，使其可以被未来的 `open`、`pipe` 或 `dup` 系统调用重新使用（见下文）。新分配的文件描述符始终是当前进程中编号最小的未使用的描述符。

File descriptors and fork interact to make I/O redirection easy to implement. fork copies the parent’s file descriptor table along with its memory, so that the child starts with exactly the same open files as the parent. The system call exec replaces the calling process’s memory but preserves its file table. This behavior allows the shell to implement I/O redirection by forking, closing and re-opening chosen file descriptors in the child, and then calling exec to run the new program. Here is a simplified version of the code a shell runs for the command cat < input.txt:

文件描述符与 `fork` 的交互使得 I/O 重定向易于实现。`fork` 会拷贝父进程的文件描述符表及其内存，因此子进程在开始时拥有与父进程完全相同的打开文件。`exec` 系统调用会替换调用进程的内存，但会保留其文件表。这种特性允许 shell 通过以下方式实现 I/O 重定向：先执行 `fork`，在子进程中关闭并重新打开特定的文件描述符，然后调用 `exec` 来运行新程序。下面是 shell 执行命令 `cat < input.txt` 时所运行代码的简化版本：

```c
char *argv[2];
argv[0] = "cat";
argv[1] = 0;
if(fork() == 0) {
    close(0);
    open("input.txt", O_RDONLY);
    exec("cat", argv);
}
```

After the child closes file descriptor 0 , open is guaranteed to use that file descriptor for the newly opened input.txt: 0 will be the smallest available file descriptor. cat then executes with file descriptor 0 (standard input) referring to input.txt. The parent process’s file descriptors are not changed by this sequence, since it modifies only the child’s descriptors.

在子进程关闭文件描述符 0 后，`open` 保证会使用该描述符来打开新的 `input.txt`：因为 0 将是最小的可用文件描述符。随后 `cat` 执行时，其文件描述符 0（标准输入）便指向了 `input.txt`。父进程的文件描述符不会被这一系列操作改变，因为它仅修改了子进程的描述符。

The code for I/O redirection in the xv6 shell works in exactly this way (7931). Recall that at this point in the code the shell has already forked the child shell and that runcmd will call exec to load the new program. The second argument to open consists of a set of flags, expressed as bits, that control what open does. The possible values are defined in the file control (fcntl) header (4000-4004) : O_RDONLY, O_WRONLY, O_RDWR, O_CREATE, and O_TRUNC, which instruct open to open the file for reading, or for writing, or for both reading and writing, to create the file if it doesn’t exist, and to truncate the file to zero length.

xv6 shell 中用于 I/O 重定向的代码正是以这种方式工作的 (7931)。请记住，在代码执行到此处时，shell 已经 fork 出了子 shell，并且 runcmd 将调用 exec 以加载新程序。`open` 的第二个参数是一组以位（bits）表示的标志位，用于控制 `open` 的行为。可能的值定义在文件控制（fcntl）头文件（4000-4004）中：`O_RDONLY`、`O_WRONLY`、`O_RDWR`、`O_CREATE` 和 `O_TRUNC`，它们分别指示 `open` 以只读、只写或读写方式打开文件，如果文件不存在则创建文件，以及将文件截断为零长度。

Now it should be clear why it is helpful that fork and exec are separate calls: between the two, the shell has a chance to redirect the child’s I/O without disturbing the I/O setup of the main shell. One could instead imagine a hypothetical combined forkexec system call, but the options for doing I/O redirection with such a call seem awkward. The shell could modify its own I/O setup before calling forkexec (and then un-do those modifications); or forkexec could take instructions for I/O redirection as arguments; or (least attractively) every program like cat could be taught to do its own I/O redirection.

现在应该很清楚为什么将 fork 和 exec 分为两个独立的调用是有帮助的了：在这两个调用之间，外壳程序（shell）有机会重定向子进程的 I/O，而不会干扰主 shell 的 I/O 设置。我们可以设想一种假设的、将两者结合的 forkexec 系统调用，但通过这种调用进行 I/O 重定向的方案似乎很笨拙。shell 可以在调用 forkexec 之前修改自身的 I/O 设置（然后再撤销这些修改）；或者 forkexec 可以将 I/O 重定向的指令作为参数；又或者（最不理想的情况）让像 cat 这样的每个程序都学会自己处理 I/O 重定向。

Although fork copies the file descriptor table, each underlying file offset is shared between parent and child. Consider this example:

虽然 fork 会复制文件描述符表，但每个底层的文件偏移量是在父进程和子进程之间共享的。考虑这个例子：

```c
if(fork() == 0) {
    write(1, "hello ", 6);
    exit(0);
} else {
    wait(0);
    write(1, "world\n", 6);
}
```

At the end of this fragment, the file attached to file descriptor 1 will contain the data hello world. The write in the parent (which, thanks to wait, runs only after the child is done) picks up where the child’s write left off. This behavior helps produce sequential output from sequences of shell commands, like (echo hello; echo world) >output.txt.

在这段代码结束时，连接到文件描述符 1 的文件将包含数据 hello world。父进程中的 write（由于 wait 的存在，它仅在子进程完成后运行）会从子进程 write 停止的地方开始写入。这种行为有助于从 shell 命令序列中产生连续的输出，例如 (echo hello; echo world) >output.txt。

The dup system call duplicates an existing file descriptor, returning a new one that refers to the same underlying I/O object. Both file descriptors share an offset, just as the file descriptors duplicated by fork do. This is another way to write hello world into a file:

dup 系统调用会复制一个现有的文件描述符，返回一个指向同一底层 I/O 对象的新描述符。这两个文件描述符共享一个偏移量，就像被 fork 复制的文件描述符一样。这是另一种将 hello world 写入文件的方法：

```c
fd = dup(1);
write(1, "hello ", 6);
write(fd, "world\n", 6);
```

Two file descriptors share an offset if they were derived from the same original file descriptor by a sequence of fork and dup calls. Otherwise file descriptors do not share offsets, even if they resulted from open calls for the same file. dup allows shells to implement commands like this: ls existing-file non-existing-file tmp1 . The tells the shell to give the command a file descriptor 2 that is a duplicate of descriptor 1. Both the name of the existing file and the error message for the non-existing file will show up in the file tmp1. The xv6 shell doesn’t support I/O redirection for the error file descriptor, but now you know how to implement it.

如果两个文件描述符是通过一系列 fork 和 dup 调用从同一个原始文件描述符派生出来的，那么它们就共享一个偏移量。否则，即使它们是通过对同一文件的 open 调用产生的，也不会共享偏移量。dup 允许 shell 实现如下命令：ls existing-file non-existing-file > tmp1 2>&1。其中的 2>&1 告诉 shell 给命令一个文件描述符 2，它是描述符 1 的副本。现有文件的名称和不存在文件的错误消息都将显示在文件 tmp1 中。xv6 shell 不支持错误文件描述符的 I/O 重定向，但现在你知道该如何实现它了。

File descriptors are a powerful abstraction, because they hide the details of what they are connected to: a process writing to file descriptor 1 may be writing to a file, to a device like the console, or to a pipe.

文件描述符是一个强大的抽象，因为它们隐藏了所连接对象的细节：一个向文件描述符 1 写入数据的进程，其写入对象可能是一个文件、一个像控制台那样的设备，或者是一个管道。

## 1.3 Pipes

A pipe is a small kernel buffer exposed to processes as a pair of file descriptors, one for reading and one for writing. Writing data to one end of the pipe makes that data available for reading from the other end of the pipe. Pipes provide a way for processes to communicate.

管道是一个小的内核缓冲区，以一对文件描述符的形式暴露给进程，一个用于读取，另一个用于写入。向管道的一端写入数据，可以使该数据从管道的另一端被读取。管道为进程间通信提供了一种方式。

The following example code runs the program wc with standard input connected to the read end of a pipe.

下面的示例代码运行了 `wc` 程序，并将其标准输入连接到了管道的读取端。

```c
int p[2];
char *argv[2];
argv[0] = "wc";
argv[1] = 0;
pipe(p);
if(fork() == 0) {
    close(0);
    dup(p[0]);
    close(p[0]);
    close(p[1]);
    exec("/bin/wc", argv);
} else {
    close(p[0]);
    write(p[1], "hello world\n", 12);
    close(p[1]);
}
```

The program calls pipe, which creates a new pipe and records the read and write file descriptors in the array p. After fork, both parent and child have file descriptors referring to the pipe. The child calls close and dup to make file descriptor zero refer to the read end of the pipe, closes the file descriptors in , and calls exec to run wc. When wc reads from its standard input, it reads from the pipe. The parent closes the read side of the pipe, writes to the pipe, and then closes the write side.

程序调用 `pipe`，创建一个新管道并将读写文件描述符记录在数组 `p` 中。调用 `fork` 后，父进程和子进程都拥有指向该管道的文件描述符。子进程调用 `close` 和 `dup` 使文件描述符 0 指向管道的读取端，关闭数组 `p` 中的文件描述符，然后调用 `exec` 运行 `wc`。当 `wc` 从其标准输入读取时，它实际上是从管道中读取。父进程关闭管道的读取端，向管道写入数据，然后关闭写入端。

If no data is available, a read on a pipe waits for either data to be written or for all file descriptors referring to the write end to be closed; in the latter case, read will return 0 , just as if the end of a data file had been reached. The fact that read blocks until it is impossible for new data to arrive is one reason that it’s important for the child to close the write end of the pipe before executing wc above: if one of wc 's file descriptors referred to the write end of the pipe, wc would never see end-of-file.

如果没有可用数据，对管道的 read 操作会等待数据写入，或者等待所有指向写端的文件描述符关闭；在后一种情况下，read 将返回 0，就像到达了数据文件的末尾一样。read 会一直阻塞直到不可能再有新数据到达，这就是为什么在上面执行 wc 之前，子进程必须关闭管道写端的一个重要原因：如果 wc 的文件描述符中有一个指向管道写端，wc 就永远不会读到文件结束符（EOF）。

The xv6 shell implements pipelines such as grep fork sh.c | wc -1 in a manner similar to the above code (7950). The child process creates a pipe to connect the left end of the pipeline with the right end. Then it calls fork and runcmd for the left end of the pipeline and fork and runcmd for the right end, and waits for both to finish. The right end of the pipeline may be a command that itself includes a pipe (e.g., ), which itself forks two new child processes (one for b and one for c ). Thus, the shell may create a tree of processes. The leaves of this tree are commands and the interior nodes are processes that wait until the left and right children complete. Pipes may seem no more powerful than temporary files: the pipeline

xv6 shell 实现管道（如 grep fork sh.c | wc -1）的方式与上述代码（7950）类似。子进程创建一个管道来连接管道线的左端和右端。然后，它为管道左端调用 fork 和 runcmd，为管道右端调用 fork 和 runcmd，并等待两者完成。管道线的右端可能本身就是一个包含管道的命令（例如 ），它会再次 fork 出两个新的子进程（一个用于 b，一个用于 c）。因此，shell 可能会创建一个进程树。这棵树的叶子节点是命令，而内部节点是等待左右子进程完成的进程。管道看起来似乎并不比临时文件更强大：管道线

```sh
echo hello world | wc
```

could be implemented without pipes as

可以在不使用管道的情况下实现为

```sh
echo hello world >/tmp/xyz; wc </tmp/xyz
```

Pipes have at least three advantages over temporary files in this situation. First, pipes automatically clean themselves up; with the file redirection, a shell would have to be careful to remove / tmp/xyz when done. Second, pipes can pass arbitrarily long streams of data, while file redirection requires enough free space on disk to store all the data. Third, pipes allow for parallel execution of pipeline stages, while the file approach requires the first program to finish before the second starts.

在这种情况下，管道相比临时文件至少有三个优势。首先，管道会自动清理；如果使用文件重定向，shell 必须在完成后小心地删除 /tmp/xyz。其次，管道可以传递任意长度的数据流，而文件重定向则需要磁盘上有足够的空闲空间来存储所有数据。第三，管道允许流水线各阶段并行执行，而文件方法则要求第一个程序运行结束后第二个程序才能开始。

## 1.4 File system

The xv6 file system provides data files, which contain uninterpreted byte arrays, and directories, which contain named references to data files and other directories. The directories form a tree, starting at a special directory called the root. A path like / refers to the file or directory named c inside the directory named b inside the directory named a in the root directory . Paths that don’t begin with / are evaluated relative to the calling process’s current directory, which can be changed with the chdir system call. Both these code fragments open the same file (assuming all the directories involved exist):

xv6 文件系统提供数据文件和目录。数据文件包含未解释的字节数组，而目录包含指向数据文件和其他目录的命名引用。这些目录形成一棵树，起始于一个被称为根目录（root）的特殊目录。像 / 这样的路径指的是根目录 下名为 a 的目录中，名为 b 的目录里，名为 c 的文件或目录。不以 / 开头的路径是相对于调用进程的当前目录进行解析的，当前目录可以通过 chdir 系统调用来更改。以下两段代码片段都打开同一个文件（假设涉及的所有目录都存在）：

```c
chdir("/a");
chdir("b");
open("c", O_RDONLY);
open("/a/b/c", O_RDONLY);
```

The first fragment changes the process’s current directory to ; the second neither refers to nor changes the process’s current directory.

第一个片段将进程的当前目录更改为 ；第二个片段既不引用也不更改进程的当前目录。

There are system calls to create new files and directories: mkdir creates a new directory, open with the O_CREATE flag creates a new data file, and mknod creates a new device file. This example illustrates all three:

有一些系统调用用于创建新的文件和目录：mkdir 创建一个新目录，带有 O_CREATE 标志的 open 创建一个新的数据文件，而 mknod 创建一个新的设备文件。以下示例说明了这三种情况：

```c
mkdir("/dir");
fd = open("/dir/file", O_CREATE|O_WRONLY);
close(fd);
mknod("/console", 1, 1);
```

mknod creates a special file that refers to a device. Associated with a device file are the major and minor device numbers (the two arguments to mknod), which uniquely identify a kernel device. When a process later opens a device file, the kernel diverts read and write system calls to the kernel device implementation instead of passing them to the file system.

mknod 用于创建一个指向设备的特殊文件。与设备文件相关联的是主设备号和次设备号（mknod 的两个参数），它们唯一地标识了一个内核设备。当进程随后打开一个设备文件时，内核会将 read 和 write 系统调用重定向到内核设备的具体实现，而不是将其传递给文件系统。

A file’s name is distinct from the file itself; the same underlying file, called an inode, can have multiple names, called links. Each link consists of an entry in a directory; the entry contains a file name and a reference to an inode. An inode holds metadata about a file, including its type (file or directory or device), its length, the location of the file’s content on disk, and the number of links to a file.

文件名与文件本身是不同的；同一个底层文件（称为 inode）可以有多个名称（称为链接 link）。每个链接由目录中的一个条目组成；该条目包含一个文件名称和对 inode 的引用。一个 inode 保存了关于文件的元数据，包括其类型（文件、目录或设备）、长度、文件内容在磁盘上的位置以及指向该文件的链接数。

The fstat system call retrieves information from the inode that a file descriptor refers to. It fills in a struct stat, defined in stat.h (4050) as:

fstat 系统调用从文件描述符所指向的 inode 中检索信息。它会填充一个 struct stat 结构体，该结构体在 stat.h (4050) 中定义如下：

```bash
#define T_DIR 1 // Directory
#define T_FILE 2 // File
#define T_DEVICE 3 // Device
struct stat {
    int dev; // File system's disk device
    uint ino; // Inode number
    short type; // Type of file
    short nlink; // Number of links to file
    uint64 size; // Size of file in bytes
};
```

The link system call creates another file system name referring to the same inode as an existing file. This fragment creates a new file named both a and b .

link 系统调用会创建另一个文件系统名称，指向与现有文件相同的 inode。这段代码片段创建了一个同时名为 a 和 b 的新文件。

```c
open("a", O_CREATE|O_WRONLY);
link("a", "b");
```

Reading from or writing to a is the same as reading from or writing to b . Each inode is identified by a unique inode number. After the code sequence above, it is possible to determine that a and b refer to the same underlying contents by inspecting the result of fstat: both will return the same inode number (ino), and the nlink count will be set to 2 .

对 a 进行读写与对 b 进行读写是完全相同的。每个 inode 都由一个唯一的 inode 编号来标识。在上述代码序列执行后，可以通过检查 fstat 的结果来确定 a 和 b 是否指向相同的底层内容：两者都将返回相同的 inode 编号（ino），并且 nlink 计数将被设置为 2。

The unlink system call removes a name from the file system. The file’s inode and the disk space holding its content are only freed when the file’s link count is zero and no file descriptors refer to it. Thus adding

unlink 系统调用从文件系统中移除一个名称。只有当文件的链接计数为零且没有文件描述符引用它时，该文件的 inode 及其存储内容的磁盘空间才会被释放。因此，在之前的代码序列最后加上

```c
unlink("a");
```

to the last code sequence leaves the inode and file content accessible as b . Furthermore,

会使 inode 和文件内容仍可通过 b 访问。此外，

```c
fd = open("/tmp/xyz", O_CREATE|O_RDWR);
unlink("/tmp/xyz");
```

is an idiomatic way to create a temporary inode with no name that will be cleaned up when the process closes fd or exits.

是一种创建无名临时 inode 的惯用方法，该 inode 会在进程关闭 fd 或退出时被清理。

Unix provides file utilities callable from the shell as user-level programs, for example mkdir, 1 n , and rm. This design allows anyone to extend the command-line interface by adding new userlevel programs. In hindsight this plan seems obvious, but other systems designed at the time of Unix often built such commands into the shell (and built the shell into the kernel).

Unix 以用户级程序的形式提供了可从 shell 调用的文件工具，例如 mkdir、ln 和 rm。这种设计允许任何人通过添加新的用户级程序来扩展命令行界面。事后看来，这个方案似乎显而易见，但在 Unix 设计之初，其他系统通常将此类命令内置在 shell 中（并将 shell 内置在内核中）。

One exception is cd, which is built into the shell (8021), cd must change the current working directory of the shell itself. If cd were run as a regular command, then the shell would fork a child process, the child process would run cd , and cd would change the child’s working directory. The parent’s (i.e., the shell’s) working directory would not change.

一个例外是 cd，它是内置在 shell 中的 (8021)。cd 必须更改 shell 本身的当前工作目录。如果将 cd 作为一个普通命令运行，那么 shell 将 fork 一个子进程，由子进程运行 cd，而 cd 只会更改子进程的工作目录。父进程（即 shell）的工作目录则不会改变。

## 1.5 Real world

Unix’s combination of “standard” file descriptors, pipes, and convenient shell syntax for operations on them was a major advance in writing general-purpose reusable programs. The idea sparked a culture of “software tools” that was responsible for much of Unix’s power and popularity, and the shell was the first so-called “scripting language.” The Unix system call interface persists today in systems like BSD, Linux, and macOS.

Unix 将“标准”文件描述符、管道以及便捷的 Shell 操作语法相结合，是编写通用可复用程序的一大进步。这一理念催生了“软件工具”文化，这也是 Unix 强大功能和流行度的主要原因，而 Shell 则是第一个所谓的“脚本语言”。Unix 系统调用接口在当今的 BSD、Linux 和 macOS 等系统中依然延续。

The Unix system call interface has been standardized through the Portable Operating System Interface (POSIX) standard. Xv6 is not POSIX compliant: it is missing many system calls (including basic ones such as lseek), and many of the system calls it does provide differ from the standard. Our main goals for xv6 are simplicity and clarity while providing a simple UNIX-like system-call interface. Several people have extended xv6 with a few more system calls and a simple C library in order to run basic Unix programs. Modern kernels, however, provide many more system calls, and many more kinds of kernel services, than xv6. For example, they support networking, windowing systems, user-level threads, drivers for many devices, and so on. Modern kernels evolve continuously and rapidly, and offer many features beyond POSIX.

Unix 系统调用接口已通过可移植操作系统接口（POSIX）标准实现了标准化。Xv6 并不符合 POSIX 标准：它缺失了许多系统调用（包括像 lseek 这样的基础调用），且其提供的许多系统调用也与标准有所不同。我们对 xv6 的主要目标是在提供简单的类 UNIX 系统调用接口的同时，保持简洁与清晰。一些人已经为 xv6 扩展了更多系统调用和一个简单的 C 库，以便运行基础的 Unix 程序。然而，现代内核比 xv6 提供了多得多的系统调用和各种内核服务。例如，它们支持网络、窗口系统、用户级线程、多种设备的驱动程序等等。现代内核持续且快速地演进，并提供了许多超越 POSIX 的特性。

Unix unified access to multiple types of resources (files, directories, and devices) with a single set of file-name and file-descriptor interfaces. This idea can be extended to more kinds of resources; a good example is Plan 9 [16], which applied the “resources are files” concept to networks, graphics, and more. However, most Unix-derived operating systems have not followed this route.

Unix 通过一套统一的文件名和文件描述符接口，实现了对多种类型资源（文件、目录和设备）的访问。这一理念可以扩展到更多种类的资源；Plan 9 [16] 就是一个很好的例子，它将“资源即文件”的概念应用于网络、图形等领域。然而，大多数源自 Unix 的操作系统并没有遵循这条路线。

The file system and file descriptors have been powerful abstractions. Even so, there are other models for operating system interfaces. Multics, a predecessor of Unix, abstracted file storage in a way that made it look like memory, producing a very different flavor of interface. The complexity of the Multics design had a direct influence on the designers of Unix, who aimed to build something simpler.

文件系统和文件描述符一直是强大的抽象。即便如此，操作系统接口仍存在其他模型。Unix 的前身 Multics 将文件存储抽象为类似内存的形式，产生了一种截然不同的接口风格。Multics 设计的复杂性直接影响了 Unix 的设计者，他们旨在构建更加简单的系统。

Xv6 does not provide a notion of users or of protecting one user from another; in Unix terms, all xv6 processes run as root.

Xv6 没有提供用户概念，也没有提供用户间的保护机制；用 Unix 的术语来说，所有 xv6 进程都以 root 身份运行。

This book examines how xv6 implements its Unix-like interface, but the ideas and concepts apply to more than just Unix. Any operating system must multiplex processes onto the underlying hardware, isolate processes from each other, and provide mechanisms for controlled inter-process communication. After studying xv6, you should be able to look at other, more complex operating systems and see the concepts underlying xv6 in those systems as well.

本书探讨了 xv6 如何实现其类 Unix 接口，但这些思想和概念不仅适用于 Unix。任何操作系统都必须将进程复用到底层硬件上，实现进程间的隔离，并提供受控的进程间通信机制。在学习完 xv6 后，你应该能够观察其他更复杂的操作系统，并发现这些系统中同样蕴含着 xv6 的底层概念。

## 1.6 Exercises

1. Write a program that uses UNIX system calls to “ping-pong” a byte between two processes over a pair of pipes, one for each direction. Measure the program’s performance, in exchanges per second.
   编写一个程序，使用 UNIX 系统调用通过一对管道（每个方向一个）在两个进程之间“乒乓”传递一个字节。测量该程序的性能，以每秒交换次数为单位。

