---
title: xv6 riscv book chapter 9：File system
date: 2025-07-27
tag: 
- OS
- risc-v
category: 
- OS
- risc-v
---

# xv6 riscv book chapter 9：File system

The purpose of a file system is to organize and store data. File systems typically support sharing of data among users and applications, as well as persistence so that data is still available after a reboot.

文件系统的目的是组织和存储数据。文件系统通常支持在用户和应用程序之间共享数据，并提供持久性，以便在重启后数据仍然可用。

The xv6 file system provides Unix-like files, directories, and pathnames (see Chapter 1), and stores its data on a virtio disk for persistence. The file system addresses several challenges:

xv6 文件系统提供了类 Unix 的文件、目录和路径名（见第 1 章），并将数据存储在 virtio 磁盘上以实现持久化。该文件系统解决了以下几个挑战：

- The file system needs on-disk data structures to represent the tree of named directories and files, to record the identities of the blocks that hold each file’s content, and to record which areas of the disk are free.
  文件系统需要磁盘上的数据结构来表示命名目录和文件组成的树状结构，记录保存每个文件内容的块的标识，并记录磁盘的哪些区域是空闲的。
- The file system must support crash recovery. That is, if a crash (e.g., power failure) occurs, the file system must still work correctly after a restart. The risk is that a crash might interrupt a sequence of updates and leave inconsistent on-disk data structures (e.g., a block that is both used in a file and marked free).
  文件系统必须支持崩溃恢复。也就是说，如果发生崩溃（例如断电），文件系统在重启后必须仍能正常工作。风险在于，崩溃可能会中断一系列更新操作，导致磁盘数据结构处于不一致状态（例如，一个块既被标记为在文件中使用，又被标记为空闲）。
- Different processes may operate on the file system at the same time, so the file-system code must coordinate to maintain invariants.
  不同的进程可能会同时操作文件系统，因此文件系统代码必须进行协调以维持不变性（invariants）。
- Accessing a disk is orders of magnitude slower than accessing memory, so the file system must maintain an in-memory cache of popular blocks.
  访问磁盘的速度比访问内存慢几个数量级，因此文件系统必须在内存中维护常用数据块的缓存。

The rest of this chapter explains how xv6 addresses these challenges.

本章接下来的部分将解释 xv6 是如何应对这些挑战的。

## 10.1 Overview

The xv6 file system implementation is organized in seven layers, shown in Figure 10.1. The disk layer reads and writes blocks on an virtio hard drive. The buffer cache layer caches disk blocks and synchronizes access to them, making sure that only one kernel process at a time can modify the data stored in any particular block. The logging layer allows higher layers to wrap updates to several blocks in a transaction, and ensures that the blocks are updated atomically in the face of crashes (i.e., all of them are updated or none). The inode layer provides individual files, each

xv6 文件系统的实现分为七层，如图 10.1 所示。磁盘层（disk layer）负责读取和写入 virtio 硬盘上的数据块。缓冲池层（buffer cache layer）缓存磁盘块并同步对它们的访问，确保每次只有一个内核进程可以修改存储在特定数据块中的数据。日志层（logging layer）允许更高层将对多个块的更新封装在一个事务中，并确保在发生崩溃时这些块能够被原子地更新（即要么全部更新，要么都不更新）。索引节点层（inode layer）提供单个文件，每个文件

| File descriptor |
| Pathname |
| Directory |
| Inode |
| Logging |
| Buffer cache |
| Disk |

represented as an inode with a unique i-number and some blocks holding the file’s data. The directory layer implements each directory as a special kind of inode whose content is a sequence of directory entries, each of which contains a file’s name and i-number. The pathname layer provides hierarchical path names like /usr/rtm/xv6/fs.c, and resolves them with recursive lookup. The file descriptor layer abstracts many Unix resources (e.g., pipes, devices, files, etc.) using the file system interface, simplifying the lives of application programmers.

文件被表示为一个具有唯一 i-节点号（i-number）的 i-节点（inode）以及一些保存文件数据的块。目录层将每个目录实现为一种特殊类型的 i-节点，其内容是一系列目录项，每个目录项包含一个文件名和 i-节点号。路径名层提供如 /usr/rtm/xv6/fs.c 之类的分层路径名，并通过递归查找来解析它们。文件描述符层使用文件系统接口抽象了许多 Unix 资源（例如管道、设备、文件等），简化了应用程序员的工作。

Disk hardware traditionally presents the data on the disk as a numbered sequence of 512-byte blocks (also called sectors): sector 0 is the first 512 bytes, sector 1 is the next, and so on. The block size that an operating system uses for its file system maybe different than the sector size that a disk uses, but typically the block size is a multiple of the sector size. Xv6 holds copies of blocks that it has read into memory in objects of type struct buf (3900). The data stored in this structure is sometimes out of sync with the disk: it might have not yet been read in from disk (the disk is working on it but hasn’t returned the sector’s content yet), or it might have been updated by software but not yet written to the disk.

磁盘硬件传统上将磁盘上的数据呈现为编号序列的 512 字节块（也称为扇区）：扇区 0 是前 512 字节，扇区 1 是接下来的 512 字节，依此类推。操作系统用于其文件系统的块大小可能与磁盘使用的扇区大小不同，但通常块大小是扇区大小的倍数。Xv6 将已读取到内存中的块副本保存在类型为 struct buf (3900) 的对象中。存储在此结构中的数据有时与磁盘不同步：它可能尚未从磁盘读入（磁盘正在处理但尚未返回扇区内容），或者它可能已被软件更新但尚未写入磁盘。

The file system must have a plan for where it stores inodes and content blocks on the disk. To do so, xv6 divides the disk into several sections, as Figure 10.2 shows. The file system does not use block 0 (it holds the boot sector). Block 1 is called the superblock; it contains metadata about the file system (the file system size in blocks, the number of data blocks, the number of inodes, and the number of blocks in the log). Blocks starting at 2 hold the log. After the log are the inodes, with multiple inodes per block. After those come bitmap blocks tracking which data blocks are in use. The remaining blocks are data blocks; each is either marked free in the bitmap block, or holds content for a file or directory. The superblock is filled in by a separate program, called mkfs, which builds an initial file system.

文件系统必须对在磁盘上存储 i-节点和内容块的位置有一个规划。为此，xv6 将磁盘分为几个部分，如图 10.2 所示。文件系统不使用块 0（它保存引导扇区）。块 1 被称为超级块（superblock）；它包含有关文件系统的元数据（以块为单位的文件系统大小、数据块的数量、i-节点的数量以及日志中的块数）。从块 2 开始的块保存日志。日志之后是 i-节点，每个块包含多个 i-节点。再之后是位图块，用于跟踪哪些数据块正在使用。剩余的块是数据块；每个数据块要么在位图块中被标记为空闲，要么保存文件或目录的内容。超级块由一个名为 mkfs 的独立程序填充，该程序负责构建初始文件系统。

The rest of this chapter discusses each layer, starting with the buffer cache. Look out for situations where well-chosen abstractions at lower layers ease the design of higher ones.

本章的其余部分将讨论每一层，从缓冲缓存（buffer cache）开始。请留意底层中精心选择的抽象如何简化高层设计的情况。

| boot | super | log | ihodes | bit map | data |  | data |
| 0 | 2 |  |  |  |  |  |  |

## 10.2 Buffer cache layer

The buffer cache has two jobs: (1) synchronize access to disk blocks to ensure that only one copy of a block is in memory and that only one kernel thread at a time uses that copy; (2) cache popular blocks so that they don’t need to be re-read from the slow disk. The code is in bio.c.

缓冲池（buffer cache）有两个任务：(1) 同步对磁盘块的访问，以确保内存中只有一个数据块副本，并且一次只有一个内核线程使用该副本；(2) 缓存常用数据块，以便不需要从缓慢的磁盘中重复读取。相关代码位于 bio.c 中。

The main interface exported by the buffer cache consists of bread and bwrite; the former obtains a buf containing a copy of a block which can be read or modified in memory, and the latter writes a modified buffer to the appropriate block on the disk. A kernel thread must release a buffer by calling brelse when it is done with it. The buffer cache uses a per-buffer sleep-lock to ensure that only one thread at a time uses each buffer (and thus each disk block); bread returns a locked buffer, and brelse releases the lock.

缓冲池导出的主要接口由 bread 和 bwrite 组成；前者获取一个包含数据块副本的 buf，该副本可以在内存中读取或修改；后者将修改后的缓冲区写入磁盘上相应的块。内核线程在完成操作后必须调用 brelse 释放缓冲区。缓冲池使用每个缓冲区独立的睡眠锁（sleep-lock）来确保每次只有一个线程使用每个缓冲区（从而确保每个磁盘块也是如此）；bread 返回一个锁定的缓冲区，而 brelse 则释放该锁。

Let’s return to the buffer cache. The buffer cache has a fixed number of buffers to hold disk blocks, which means that if the file system asks for a block that is not already in the cache, the buffer cache must recycle a buffer currently holding some other block. The buffer cache recycles the least recently used buffer for the new block. The assumption is that the least recently used buffer is the one least likely to be used again soon.

让我们回到缓冲池。缓冲池拥有固定数量的缓冲区来保存磁盘块，这意味着如果文件系统请求一个尚未在缓存中的块，缓冲池必须回收当前持有其他块的缓冲区。缓冲池会为新块回收最近最少使用（LRU）的缓冲区。其假设是，最近最少使用的缓冲区是近期最不可能被再次使用的。

## 10.3 Code: Buffer cache

The buffer cache is a doubly-linked list of buffers. The function binit, called by main (1176), initializes the list with the NBUF buffers in the static array buf (4292-4301). All other access to the buffer cache refer to the linked list via bcache.head, not the buf array.

缓冲池是一个缓冲区的双向链表。由 main (1176) 调用的 binit 函数使用静态数组 buf (4292-4301) 中的 NBUF 个缓冲区初始化该链表。所有对缓冲池的其他访问都通过 bcache.head 引用该链表，而不是直接访问 buf 数组。

A buffer has two state fields associated with it. The field valid indicates that the buffer contains a copy of the block. The field disk indicates that the buffer content has been handed to the disk, which may change the buffer (e.g., write data from the disk into data). bread (4352) calls bget to get a buffer for the given sector (4356). If the buffer needs to be read from disk, bread calls virtio_disk_rw to do that before returning the buffer. bget (4308) scans the buffer list for a buffer with the given device and sector numbers (43144322). If there is such a buffer, bget acquires the sleep-lock for the buffer. bget then returns the locked buffer.

一个缓冲区包含两个与其相关的状态字段。valid 字段表示该缓冲区包含磁盘块的一个副本。disk 字段表示缓冲区内容已交给磁盘处理，这可能会改变缓冲区（例如，将数据从磁盘写入 data 字段）。bread (4352) 调用 bget 来获取给定扇区的缓冲区 (4356)。如果该缓冲区需要从磁盘读取，bread 会在返回缓冲区之前调用 virtio_disk_rw 来完成此操作。bget (4308) 扫描缓冲区列表，查找具有给定设备号和扇区号的缓冲区 (4314-4322)。如果存在这样的缓冲区，bget 会获取该缓冲区的睡眠锁（sleep-lock）。然后 bget 返回该锁定后的缓冲区。

If there is no cached buffer for the given sector, bget must make one, possibly reusing a buffer that held a different sector. It scans the buffer list a second time, looking for a buffer that is not in use ; any such buffer can be used. bget edits the buffer metadata to record the new device and sector number and acquires its sleep-lock. Note that the assignment valid ensures that bread will read the block data from disk rather than incorrectly using the buffer’s previous contents.

如果给定扇区没有缓存的缓冲区，bget 必须创建一个，可能会重用一个原本持有不同扇区的缓冲区。它会第二次扫描缓冲区列表，寻找一个未在使用中的缓冲区 ；任何这样的缓冲区都可以被使用。bget 修改缓冲区的元数据以记录新的设备号和扇区号，并获取其睡眠锁。请注意，赋值语句 valid 确保了 bread 将从磁盘读取块数据，而不是错误地使用缓冲区之前的内容。

It is important that there is at most one cached buffer per disk sector, to ensure that readers see writes, and because the file system uses locks on buffers for synchronization. bget ensures this invariant by holding the bcache.lock continuously from the first loop’s check of whether the block is cached through the second loop’s declaration that the block is now cached (by setting dev, blockno, and refcnt). This causes the check for a block’s presence and (if not present) the designation of a buffer to hold the block to be atomic.

确保每个磁盘扇区最多只有一个缓存缓冲区至关重要，这既是为了确保读者能看到写操作，也是因为文件系统使用缓冲区上的锁来进行同步。bget 通过持续持有 bcache.lock 来保证这一不变性，从第一轮循环检查块是否已缓存，一直到第二轮循环声明该块现在已被缓存（通过设置 dev、blockno 和 refcnt）。这使得检查块是否存在以及（如果不存在）指定一个缓冲区来持有该块的操作是原子的。

It is safe for bget to acquire the buffer’s sleep-lock outside of the bcache.lock critical section, since the non-zero refcnt prevents the buffer from being re-used for a different disk block. The sleep-lock protects reads and writes of the block’s buffered content, while the bcache.lock protects information about which blocks are cached.

bget 在 bcache.lock 临界区之外获取缓冲区的睡眠锁是安全的，因为非零的 refcnt 防止了该缓冲区被重用于不同的磁盘块。睡眠锁保护对块中缓冲内容的读写，而 bcache.lock 则保护有关哪些块被缓存的信息。

If all the buffers are busy, then too many processes are simultaneously executing file system calls; bget panics. A more graceful response might be to sleep until a buffer became free, though there would then be a possibility of deadlock.

如果所有缓冲区都处于忙碌状态，则说明有太多的进程在同时执行文件系统调用；此时 bget 会触发 panic。更优雅的响应方式可能是让进程休眠直到有缓冲区空闲，尽管这样做可能会导致死锁。

Once bread has read the disk (if needed) and returned the buffer to its caller, the caller has exclusive use of the buffer and can read or write the data bytes. If the caller does modify the buffer, it must call bwrite to write the changed data to disk before releasing the buffer. bwrite (4366) calls virtio_disk_rw to talk to the disk hardware.

一旦 bread 完成了磁盘读取（如果需要）并将缓冲区返回给调用者，调用者就拥有了该缓冲区的排他使用权，可以读取或写入数据字节。如果调用者修改了缓冲区，则必须在释放缓冲区之前调用 bwrite 将更改后的数据写入磁盘。bwrite (4366) 调用 virtio_disk_rw 与磁盘硬件进行交互。

When the caller is done with a buffer, it must call brelse to release it. (The name brelse, a shortening of b-release, is cryptic but worth learning: it originated in Unix and is used in BSD, Linux, and Solaris too.) brelse (4376) releases the sleep-lock and moves the buffer to the front of the linked list (4387-4392). Moving the buffer causes the list to be ordered by how recently the buffers were used (meaning released): the first buffer in the list is the most recently used, and the last is the least recently used. The two loops in bget take advantage of this: the scan for an existing buffer must process the entire list in the worst case, but checking the most recently used buffers first (starting at bcache.head and following next pointers) will reduce scan time when there is good locality of reference. The scan to pick a buffer to reuse picks the least recently used buffer by scanning backward (following prev pointers).

当调用者使用完缓冲区后，必须调用 brelse 来释放它。（brelse 这个名字是 b-release 的缩写，虽然晦涩但值得学习：它起源于 Unix，并同样被用于 BSD、Linux 和 Solaris 中。）brelse (4376) 释放睡眠锁并将缓冲区移动到链表的头部 (4387-4392)。移动缓冲区的操作使得链表按缓冲区的最近使用（即释放）情况进行排序：链表中的第一个缓冲区是最近使用的，最后一个是最近最少使用的。bget 中的两个循环利用了这一点：在最坏的情况下，扫描现有缓冲区的过程必须处理整个链表，但优先检查最近使用的缓冲区（从 bcache.head 开始并沿着 next 指针查找）可以在具有良好引用局部性时减少扫描时间。而选择可复用缓冲区的扫描则通过反向扫描（沿着 prev 指针）来选取最近最少使用的缓冲区。

## 10.4 Logging layer

One of the most interesting problems in file system design is crash recovery. The problem arises because many file-system operations involve multiple writes to the disk, and a crash after a subset of the writes may leave the on-disk file system in an inconsistent state. For example, suppose a crash occurs during file truncation (setting the length of a file to zero and freeing its content blocks). Depending on the order of the disk writes, the crash may either leave an inode with a reference to a content block that is marked free, or it may leave an allocated but unreferenced content block.

文件系统设计中最有趣的问题之一是崩溃恢复。产生这个问题的原因是许多文件系统操作涉及多次磁盘写入，而如果在完成部分写入后发生崩溃，可能会使磁盘上的文件系统处于不一致的状态。例如，假设在文件截断（将文件长度设为零并释放其内容块）期间发生崩溃。取决于磁盘写入的顺序，崩溃可能会导致一个 inode 仍然引用着一个已被标记为空闲的内容块，或者导致一个内容块已被分配但未被任何 inode 引用。

The latter is relatively benign, but an inode that refers to a freed block is likely to cause serious problems after a reboot. After reboot, the kernel might allocate that block to another file, and now we have two different files pointing unintentionally to the same block. If xv6 supported multiple users, this situation could be a security problem, since the old file’s owner would be able to read and write blocks in the new file, owned by a different user.

后一种情况相对无害，但引用了已释放块的 inode 在重启后可能会导致严重问题。重启后，内核可能会将该块分配给另一个文件，这样就会出现两个不同的文件无意中指向同一个块的情况。如果 xv6 支持多用户，这种情况可能会导致安全问题，因为旧文件的所有者将能够读取和写入属于另一个用户的、新文件中的块。

Xv6 solves the problem of crashes during file-system operations with a simple form of logging. An xv6 system call does not directly write the on-disk file system data structures. Instead, it places a description of all the disk writes it wishes to make in a log on the disk. Once the system call has logged all of its writes, it writes a special commit record to the disk indicating that the log contains a complete operation. At that point the system call copies the writes to the on-disk file system data structures. After those writes have completed, the system call erases the log on disk.

Xv6 通过一种简单形式的日志机制解决了文件系统操作期间的崩溃问题。xv6 的系统调用并不直接修改磁盘上的文件系统数据结构。相反，它会将所有准备进行的磁盘写操作描述记录在磁盘的一个日志（log）中。一旦系统调用将其所有的写操作都记录在日志中，它就会向磁盘写入一条特殊的提交记录（commit record），表明该日志包含了一个完整的操作。此时，系统调用才将这些写操作复制到磁盘上的文件系统数据结构中。在这些写操作完成后，系统调用会擦除磁盘上的日志。

If the system should crash and reboot, the file-system code recovers from the crash as follows, before running any processes. If the log is marked as containing a complete operation, then the recovery code copies the writes to where they belong in the on-disk file system. If the log is not marked as containing a complete operation, the recovery code ignores the log. The recovery code finishes by erasing the log.

如果系统发生崩溃并重启，文件系统代码在运行任何进程之前，会按如下方式从崩溃中恢复。如果日志被标记为包含一个完整的操作，那么恢复代码会将这些写操作复制到它们在磁盘文件系统中所属的位置。如果日志未被标记为包含完整操作，恢复代码则会忽略该日志。恢复代码最后通过擦除日志来完成工作。

Why does xv6’s log solve the problem of crashes during file system operations? If the crash occurs before the operation commits, then the log on disk will not be marked as complete, the recovery code will ignore it, and the state of the disk will be as if the operation had not even started. If the crash occurs after the operation commits, then recovery will replay all of the operation’s writes, perhaps repeating them if the operation had started to write them to the on-disk data structure. In either case, the log makes operations atomic with respect to crashes: after recovery, either all of the operation’s writes appear on the disk, or none of them appear.

为什么 xv6 的日志能解决文件系统操作期间的崩溃问题？如果崩溃发生在操作提交之前，那么磁盘上的日志将不会被标记为完成，恢复代码会忽略它，磁盘状态将如同该操作从未开始过一样。如果崩溃发生在操作提交之后，恢复代码将重放该操作的所有写操作，如果操作之前已经开始向磁盘数据结构写入，那么恢复时可能会重复写入。在任何一种情况下，日志都使操作相对于崩溃具有原子性：恢复之后，该操作的所有写操作要么全部出现在磁盘上，要么全部不出现。

## 10.5 Log design

The log resides at a known fixed location, specified in the superblock. It consists of a header block followed by a sequence of updated block copies (“logged blocks”). The header block contains an array of sector numbers, one for each of the logged blocks, and the count of log blocks. The count in the header block on disk is either zero, indicating that there is no transaction in the log, or nonzero, indicating that the log contains a complete committed transaction with the indicated number of logged blocks. Xv6 writes the header block when a transaction commits, but not before, and sets the count to zero after copying the logged blocks to the file system. Thus a crash midway through a transaction will result in a count of zero in the log’s header block; a crash after a commit will result in a non-zero count.

日志位于超级块（superblock）中指定的已知固定位置。它由一个头部块（header block）和一系列更新后的块副本（“日志块”）组成。头部块包含一个扇区号数组（每个日志块对应一个）以及日志块的数量。磁盘头部块中的数量要么为零（表示日志中没有事务），要么为非零（表示日志包含一个已提交的完整事务，并指明了日志块的数量）。Xv6 仅在事务提交时写入头部块，而不会在此之前写入，并在将日志块复制到文件系统后将数量设为零。因此，事务执行中途发生的崩溃会导致日志头部块中的数量为零；提交后的崩溃则会导致数量为非零。

Each system call’s code indicates the start and end of the sequence of writes that must be atomic with respect to crashes. To allow concurrent execution of file-system operations by different processes, the logging system can accumulate the writes of multiple system calls into one transaction. Thus a single commit may involve the writes of multiple complete system calls. To avoid splitting a system call across transactions, the logging system only commits when no file-system system calls are underway.

每个系统调用的代码都会标明相对于崩溃必须保持原子性的写操作序列的起始和结束。为了允许不同进程并发执行文件系统操作，日志系统可以将多个系统调用的写操作累积到一个事务中。因此，一次提交可能涉及多个完整系统调用的写操作。为了避免将单个系统调用拆分到不同的事务中，日志系统仅在没有文件系统系统调用正在进行时才进行提交。

The idea of committing several transactions together is known as group commit. Group commit reduces the number of disk operations because it amortizes the fixed cost of a commit over multiple operations. Group commit also hands the disk system more concurrent writes at the same time, perhaps allowing the disk to write them all during a single disk rotation. Xv6’s virtio driver doesn’t support this kind of batching, but xv6’s file system design allows for it.

将多个事务一起提交的想法被称为组提交（group commit）。组提交减少了磁盘操作的次数，因为它将提交的固定开销分摊到了多个操作中。组提交还同时向磁盘系统交付了更多的并发写入，这可能允许磁盘在单次旋转期间完成所有写入。xv6 的 virtio 驱动程序不支持这种批处理，但 xv6 的文件系统设计允许这样做。

Xv6 dedicates a fixed amount of space on the disk to hold the log. The total number of blocks written by the system calls in a transaction must fit in that space. This has two consequences. No single system call can be allowed to write more distinct blocks than there is space in the log. This is not a problem for most system calls, but two of them can potentially write many blocks: write and unlink. A large file write may write many data blocks and many bitmap blocks as well as an inode block; unlinking a large file might write many bitmap blocks and an inode. Xv6’s write system call breaks up large writes into multiple smaller writes that fit in the log, and unlink doesn’t cause problems because in practice the xv6 file system uses only one bitmap block. The other consequence of limited log space is that the logging system cannot allow a system call to start unless it is certain that the system call’s writes will fit in the space remaining in the log.

xv6 在磁盘上分配了固定数量的空间来存放日志。块的总数事务中系统调用所写入的所有块必须能容纳在该空间内。这产生了两个后果。不允许任何单个系统调用写入比日志空间更多的不同块。对于大多数系统调用来说这不是问题，但其中有两个可能会写入大量块：write 和 unlink。写入大文件可能会写入许多数据块、许多位图块以及一个 inode 块；删除大文件可能会写入许多位图块和一个 inode。xv6 的 write 系统调用将大额写入分解为多个能容纳在日志中的较小写入，而 unlink 不会产生问题，因为在实践中 xv6 文件系统仅使用一个位图块。有限日志空间的另一个后果是，日志系统除非确定系统调用的写入能容纳在日志剩余空间内，否则不能允许该系统调用开始执行。

## 10.6 Code: logging

A typical use of the log in a system call looks like this:

系统调用中日志的典型用法如下所示：

```c
begin_op();
...
bp = bread(...);
bp->data[...] = ...;
log_write(bp);
...
end_op();
```

begin_op (4702) waits until the logging system is not currently committing, and until there is enough unreserved log space to hold the writes from this call. log.outstanding counts the number of system calls that have reserved log space; the total reserved space is log.outstanding times MAXOPBLOCKS. Incrementing log.outstanding both reserves space and prevents a commit from occurring during this system call. The code conservatively assumes that each system call might write up to MAXOPBLOCKS distinct blocks. log_write (4790) acts as a proxy for bwrite. It records the block’s sector number in memory, reserving it a slot in the log on disk, and pins the buffer in the block cache to prevent the block cache from evicting it. The block must stay in the cache until committed: until then, the cached copy is the only record of the modification; it cannot be written to its place on disk until after commit; and other reads in the same transaction must see the modifications. log_write notices when a block is written multiple times during a single transaction, and allocates that block the same slot in the log. This optimization is often called absorption. It is common that, for example, the disk block containing inodes of several files is written several times within a transaction. By absorbing several disk writes into one, the file system can save log space and can achieve better performance because only one copy of the disk block must be written to disk. end_op (4722) first decrements the count of outstanding system calls. If the count is now zero, it commits the current transaction by calling commit(). There are four stages in this process. write_log() (4754) copies each block modified in the transaction from the buffer cache to its slot in the log on disk. write_head() (4668) writes the header block to disk: this is the commit point, and a crash after the write will result in recovery replaying the transaction’s writes from the log. install_trans (4619) reads each block from the log and writes it to the proper place in the file system. Finally end_op writes the log header with a count of zero; this has to happen before the next transaction starts writing logged blocks, so that a crash doesn’t result in recovery using one transaction’s header with the subsequent transaction’s logged blocks. recover_from_log(4682) is called from initlog(4606), which is called from fsinit(4891) during boot before the first user process runs (2666). It reads the log header, and mimics the actions of end_op if the header indicates that the log contains a committed transaction.

begin_op (4702) 会一直等待，直到日志系统当前未在进行提交，并且有足够的未保留日志空间来容纳该调用的写入操作。log.outstanding 用于统计已保留日志空间的系统调用数量；总保留空间为 log.outstanding 乘以 MAXOPBLOCKS。增加 log.outstanding 既保留了空间，又防止了在该系统调用期间发生提交。代码保守地假设每个系统调用最多可能写入 MAXOPBLOCKS 个不同的块。log_write (4790) 充当了 bwrite 的代理。它在内存中记录块的扇区号，在磁盘日志中为其预留一个槽位，并固定（pin）块缓存中的缓冲区，以防止块缓存将其驱逐。该块必须留在缓存中直到提交：在此之前，缓存的副本是修改的唯一记录；在提交之前，它不能被写入磁盘的原始位置；并且同一事务中的其他读取必须能看到这些修改。log_write 会察觉到一个块在单个事务中被多次写入的情况，并为该块分配日志中的同一个槽位。这种优化通常被称为吸收（absorption）。例如，包含多个文件 inode 的磁盘块在一次事务中被多次写入是很常见的。通过将多次磁盘写入吸收为一次，文件系统可以节省日志空间，并获得更好的性能，因为只需将磁盘块的一个副本写入磁盘。end_op (4722) 首先递减正在进行的系统调用的计数。如果计数变为零，它将通过调用 commit() 来提交当前事务。这个过程分为四个阶段。write_log() (4754) 将事务中修改的每个块从缓冲区缓存复制到磁盘日志中对应的槽位。write_head() (4668) 将头部块写入磁盘：这是提交点，写入后的崩溃将导致恢复程序从日志中重放该事务的写入。install_trans (4619) 从日志中读取每个块并将其写入到磁盘中正确的位置。文件系统。最后，`end_op` 将计数值为零的日志头写入磁盘；这必须在下一个事务开始写入日志块之前完成，这样崩溃才不会导致恢复程序使用前一个事务的日志头去处理后续事务的日志块。`recover_from_log`(4682) 由 `initlog`(4606) 调用，而 `initlog` 则在启动期间、第一个用户进程运行 (2666) 之前的 `fsinit`(4891) 中被调用。它读取日志头，如果日志头显示日志包含一个已提交的事务，它就会模仿 `end_op` 的操作。

An example use of the log occurs in filewrite (5803). The transaction looks like this:

日志使用的一个例子出现在 `filewrite` (5803) 中。该事务如下所示：

```c
begin_op();
ilock(f->ip);
r = writei(f->ip, ...);
iunlock(f->ip);
end_op();
```

This code is wrapped in a loop that breaks up large writes into individual transactions of just a few sectors at a time, to avoid overflowing the log. The call to writei writes many blocks as part of this transaction: the file’s inode, one or more bitmap blocks, and some data blocks.

这段代码被包裹在一个循环中，该循环将大的写入操作分解为每次仅几个扇区的独立事务，以避免日志溢出。在这一事务中，对 `writei` 的调用会写入多个块：文件的 inode、一个或多个位图块以及一些数据块。

## 10.7 Code: Block allocator

File and directory content is stored in disk blocks, which must be allocated from a free pool. Xv6’s block allocator maintains a free bitmap on disk, with one bit per block. A zero bit indicates that the corresponding block is free; a one bit indicates that it is in use. The program mkfs sets the bits corresponding to the boot sector, superblock, log blocks, inode blocks, and bitmap blocks.

文件和目录内容存储在磁盘块中，这些块必须从空闲池中分配。Xv6 的块分配器在磁盘上维护一个空闲位图，每个块对应一个比特位。比特位为 0 表示对应的块是空闲的；比特位为 1 表示它正在使用中。程序 `mkfs` 会设置对应于启动扇区、超级块、日志块、inode 块和位图块的比特位。

The block allocator provides two functions: balloc allocates a new disk block, and bfree frees a block. balloc The loop in balloc at (4923) considers every block, starting at block 0 up to sb. size, the number of blocks in the file system. It looks for a block whose bitmap bit is zero, indicating that it is free. If balloc finds such a block, it updates the bitmap and returns the block. For efficiency, the loop is split into two pieces. The outer loop reads each block of bitmap bits. The inner loop checks all Bits-Per-Block (BPB) bits in a single bitmap block. The race that might occur if two processes try to allocate a block at the same time is prevented by the fact that the buffer cache only lets one process use any one bitmap block at a time. bfree (4952) finds the right bitmap block and clears the right bit. Again the exclusive use implied by bread and brelse avoids the need for explicit locking.

块分配器提供了两个函数：`balloc` 用于分配一个新的磁盘块，而 `bfree` 用于释放一个块。`balloc` 中位于 (4923) 的循环会遍历每一个块，从块 0 开始直到 `sb.size`（文件系统中的块总数）。它寻找位图位为零的块，这表示该块是空闲的。如果 `balloc` 找到了这样一个块，它会更新位图并返回该块。为了提高效率，该循环被分为两部分。外层循环读取位图位的每个块。内层循环检查单个位图块中的所有每块位数 (BPB)。如果两个进程尝试同时分配一个块，可能发生的竞争会被缓冲区缓存（buffer cache）所阻止，因为缓冲区缓存每次只允许一个进程使用任何一个位图块。`bfree` (4952) 找到正确的位图块并清除相应的位。同样，由 `bread` 和 `brelse` 隐含的排他性使用避免了对显式锁的需求。

As with much of the code described in the remainder of this chapter, balloc and bfree must be called inside a transaction.

与本章剩余部分描述的大多数代码一样，`balloc` 和 `bfree` 必须在事务（transaction）内部调用。

## 10.8 Inode layer

The term inode can have one of two related meanings. It might refer to the on-disk data structure containing a file’s size and list of data block numbers. Or “inode” might refer to an in-memory inode, which contains a copy of the on-disk inode as well as extra information needed within the kernel.

术语“inode”可以有两种相关的含义。它可能指代磁盘上的数据结构，其中包含文件的大小和数据块号列表。或者，“inode”可能指代内存中的 inode，它包含磁盘 inode 的副本以及内核所需的额外信息。

The on-disk inodes are packed into a contiguous area of disk called the inode blocks. Every inode is the same size, so it is easy, given a number n , to find the nth inode on the disk. In fact, this number n , called the inode number or i -number, is how inodes are identified in the implementation.

磁盘上的 inode 被打包到磁盘中一个称为 inode 块的连续区域。每个 inode 的大小都相同，因此给定编号 n，很容易找到磁盘上的第 n 个 inode。事实上，这个编号 n（被称为 inode 编号或 i-number）就是实现中标识 inode 的方式。

The on-disk inode is defined by a struct dinode (4131). The type field distinguishes between files, directories, and special files (devices). A type of zero indicates that an on-disk inode is free. The nlink field counts the number of directory entries that refer to this inode, in order to recognize when the on-disk inode and its data blocks should be freed. The size field records the number of bytes of content in the file. The addrs array records the block numbers of the disk blocks holding the file’s content.

磁盘上的 inode 由 `struct dinode` (4131) 定义。`type` 字段用于区分文件、目录和特殊文件（设备）。`type` 为零表示该磁盘 inode 是空闲的。`nlink` 字段记录引用该 inode 的目录项数量，以便识别何时应当释放该磁盘 inode 及其数据块。`size` 字段记录文件内容的字节数。`addrs` 数组记录持有文件内容的磁盘块的块号。

The kernel keeps the set of active inodes in memory in a table called itable; struct inode (4216) is the in-memory copy of a struct dinode on disk. The kernel stores an inode in memory only if there are pointers referring to that inode. The ref field counts the number of pointers referring to the in-memory inode, and the kernel discards the inode from memory if the reference count drops to zero. The iget and iput functions acquire and release pointers to an inode, modifying the reference count. Pointers to an inode can come from file descriptors, current working directories, and transient kernel code such as kexec.

内核在内存中维护一个名为 `itable` 的表，其中包含一组活跃的 inode；`struct inode` (4216) 是磁盘上 `struct dinode` 的内存副本。只有当存在指向该 inode 的 指针时，内核才会在内存中存储该 inode。`ref` 字段记录指向内存中 inode 的 指针数量，如果引用计数降至零，内核将从内存中丢弃该 inode。`iget` 和 `iput` 函数用于获取和释放指向 inode 的指针，并修改引用计数。指向 inode 的指针可以来自文件描述符、当前工作目录以及诸如 `kexec` 之类的瞬态内核代码。

There are four lock or lock-like mechanisms in xv6’s inode code. itable. lock protects the invariant that an inode is present in the inode table at most once, and the invariant that an inmemory inode’s ref field counts the number of in-memory pointers to the inode. Each in-memory inode has a lock field containing a sleep-lock, which ensures exclusive access to the inode’s fields (such as file length) as well as to the inode’s file or directory content blocks. An inode’s ref, if it is greater than zero, causes the system to maintain the inode in the table, and not re-use the table entry for a different inode. Finally, each inode contains a nlink field (on disk and copied in memory if in memory) that counts the number of directory entries that refer to a file; xv6 won’t free an inode if its link count is greater than zero.

xv6 的 inode 代码中有四种锁或类锁机制。`itable.lock` 保护了以下不变性：一个 inode 最多在 inode 表中出现一次，且内存中 inode 的 `ref` 字段记录了指向该 inode 的内存指针数量。每个内存中的 inode 都有一个包含睡眠锁（sleep-lock）的 `lock` 字段，它确保对 inode 字段（如文件长度）以及 inode 的文件或目录内容块的排他性访问。如果 inode 的 `ref` 大于零，系统会将该 inode 保留在表中，且不会将该表项重用于其他 inode。最后，每个 inode 包含一个 `nlink` 字段（在磁盘上，若在内存中则也会复制到内存），用于记录引用该文件的目录项数量；如果链接计数大于零，xv6 不会释放该 inode。

A struct inode pointer returned by iget() is guaranteed to be valid until the corresponding call to iput (); the inode won’t be deleted, and the memory referred to by the pointer won’t be re-used for a different inode. iget () provides non-exclusive access to an inode, so that there can be many pointers to the same inode. Many parts of the file-system code depend on this behavior of iget (), both to hold long-term references to inodes (as open files and current directories) and to prevent races while avoiding deadlock in code that manipulates multiple inodes (such as pathname lookup).

`iget()` 返回的 `struct inode` 指针保证在调用相应的 `iput()` 之前保持有效；该 inode 不会被删除，且指针引用的内存不会被重用于其他 inode。`iget()` 提供对 inode 的非排他性访问，因此可以有多个指针指向同一个 inode。文件系统代码的许多部分都依赖于 `iget()` 的这种行为，既为了持有对 inode 的长期引用（如打开的文件和当前目录），也为了在操作多个 inode 的代码（如路径名查找）中防止竞争并避免死锁。

The struct inode that iget returns may not have any useful content. In order to ensure it holds a copy of the on-disk inode, code must call ilock. This locks the inode (so that no other process can ilock it) and reads the inode from the disk, if it has not already been read. iunlock releases the lock on the inode. Separating acquisition of inode pointers from locking helps avoid deadlock in some situations, for example during directory lookup. Multiple processes can hold a C pointer to an inode returned by iget, but only one process can lock the inode at a time.

`iget` 返回的 `struct inode` 可能不包含任何有用内容。为了确保它持有磁盘 inode 的副本，代码必须调用 `ilock`。这会锁定该 inode（以便其他进程无法对其调用 `ilock`），并从磁盘读取该 inode（如果尚未读取）。`iunlock` 释放 inode 上的锁。将获取 inode 指针与锁定操作分离有助于在某些情况下避免死锁，例如在目录查找期间。多个进程可以持有由 `iget` 返回的指向某个 inode 的 C 指针，但一次只能有一个进程锁定该 inode。

The inode table only stores inodes to which kernel code or data structures hold C pointers. Its main job is synchronizing access by multiple processes. The inode table also happens to cache frequently-used inodes, but caching is secondary; if an inode is used frequently, the buffer cache will probably keep it in memory. Code that modifies an in-memory inode writes it to disk with iupdate.

inode 表仅存储内核代码或数据结构持有其 C 指针的 inode。它的主要工作是同步多个进程的访问。inode 表也恰好缓存了常用 inode，但缓存是次要的；如果一个 inode 被频繁使用，缓冲区缓存（buffer cache）可能会将其保留在内存中。修改内存中 inode 的代码会通过以下方式将其写入磁盘： iupdate。

## 10.9 Code: Inodes

To allocate a new inode (for example, when creating a file), xv6 calls ialloc (5059), ialloc is similar to balloc: it loops over the inode structures on the disk, one block at a time, looking for one that is marked free. When it finds one, it claims it by writing the new type to the disk and then returns an entry from the inode table with the tail call to iget (5073). The correct operation of ialloc depends on the fact that only one process at a time can be holding a reference to bp: ialloc can be sure that some other process does not simultaneously see that the inode is available and try to claim it. iget (5107) looks through the inode table for an active entry (ip->ref ) with the desired device and inode number. If it finds one, it returns a new reference to that inode (5116-5120). As iget scans, it records the position of the first empty slot (5121-5122), which it uses if it needs to allocate a table entry.

为了分配一个新的 inode（例如在创建文件时），xv6 会调用 ialloc (5059)。ialloc 与 balloc 类似：它逐块遍历磁盘上的 inode 结构，寻找被标记为空闲的 inode。当找到一个空闲 inode 时，它通过将新类型写入磁盘来占用该 inode，然后通过尾递归调用 iget (5073) 返回 inode 表中的一个条目。ialloc 的正确运行依赖于这样一个事实：一次只能有一个进程持有对 bp 的引用；因此 ialloc 可以确保其他进程不会同时看到该 inode 可用并试图占用它。iget (5107) 在 inode 表中查找具有指定设备号和 inode 编号的活动条目（ip->ref > 0）。如果找到了，它会返回对该 inode 的一个新引用 (5116-5120)。在 iget 扫描时，它会记录第一个空槽位的位置 (5121-5122)，以便在需要分配表条目时使用。

Code must lock the inode using ilock before reading or writing its metadata or content. ilock (5153) uses a sleep-lock for this purpose. Once ilock has exclusive access to the inode, it reads the inode from disk (more likely, the buffer cache) if needed. The function iunlock (5181) releases the sleep-lock, which may cause any processes sleeping to be woken up. iput (5208) releases a C pointer to an inode by decrementing the reference count (5231). If this is the last reference, the inode’s slot in the inode table is now free and can be re-used for a different inode.

在读取或写入 inode 的元数据或内容之前，代码必须使用 ilock 锁定该 inode。ilock (5153) 为此使用了一个睡眠锁（sleep-lock）。一旦 ilock 获得了对 inode 的排他性访问权，它会在必要时从磁盘（更可能是缓冲区缓存）读取 inode。函数 iunlock (5181) 会释放睡眠锁，这可能会唤醒任何正在睡眠的进程。iput (5208) 通过递减引用计数 (5231) 来释放指向 inode 的 C 指针。如果这是最后一个引用，则该 inode 在 inode 表中的槽位现在变为空闲状态，可以被重新用于其他 inode。

If iput sees that there are no C pointer references to an inode and that the inode has no links to it (occurs in no directory), then the inode and its data blocks must be freed. iput calls itrunc to truncate the file to zero bytes, freeing the data blocks; sets the inode type to 0 (unallocated); and writes the inode to disk (5213).

如果 iput 发现既没有指向该 inode 的 C 指针引用，且该 inode 也没有任何链接（即不存在于任何目录中），那么该 inode 及其数据块必须被释放。iput 调用 itrunc 将文件截断为零字节，从而释放数据块；将 inode 类型设置为 0（未分配）；并将 inode 写入磁盘 (5213)。

The locking protocol in iput in the case in which it frees the inode deserves a closer look. One danger is that a concurrent thread might be waiting in ilock to use this inode (e.g., to read a file or list a directory), and won’t be prepared to find that the inode is no longer allocated. This can’t happen because there is no way for a system call to get a pointer to an in-memory inode if it has no links to it and ip->ref is one. That one reference is the reference owned by the thread calling iput. The other main danger is that a concurrent call to ialloc might choose the same inode that iput is freeing. This can happen only after the iupdate writes the disk so that the inode has type zero. This race is benign; the allocating thread will politely wait to acquire the inode’s sleep-lock before reading or writing the inode, at which point iput is done with it. iput () can write to the disk. This means that any system call that uses the file system may write to the disk, because the system call may be the last one having a reference to the file. Even calls like read() that appear to be read-only, may end up calling iput (). This, in turn, means that even read-only system calls must be wrapped in transactions if they use the file system.

在 `iput` 释放 inode 的情况下，其锁定协议值得仔细研究。一种危险是，并发线程可能正在 `ilock` 中等待使用该 inode（例如，为了读取文件或列出目录内容），并且没有准备好应对该 inode 不再被分配的情况。这种情况不会发生，因为如果一个 inode 没有链接且 `ip->ref` 为 1，系统调用就无法获取指向该内存 inode 的指针。这仅有的一个引用正是由调用 `iput` 的线程所持有的。另一个主要的危险是，并发调用的 `ialloc` 可能会选择 `iput` 正在释放的同一个 inode。这只有在 `iupdate` 写入磁盘使 inode 类型变为零之后才可能发生。这种竞争是无害的；分配线程在读写该 inode 之前，会礼貌地等待获取该 inode 的睡眠锁（sleep-lock），而此时 `iput` 已经处理完该 inode 了。`iput()` 可能会写入磁盘。这意味着任何使用文件系统的系统调用都可能写入磁盘，因为该系统调用可能是最后一个持有该文件引用的调用。即使是像 `read()` 这样看似只读的调用，最终也可能调用 `iput()`。这反过来意味着，如果只读系统调用使用了文件系统，也必须将其封装在事务中。

There is a challenging interaction between iput () and crashes. iput () doesn’t truncate a file immediately when the link count for the file drops to zero, because some process might still hold a reference to the inode in memory: a process might still be reading and writing to the file, because

`iput()` 与崩溃之间存在一种具有挑战性的交互。当文件的链接计数降至零时，`iput()` 不会立即截断文件，因为某些进程可能仍持有内存中该 inode 的引用：进程可能仍在读写该文件，因为


it successfully opened it. But, if a crash happens before the last process closes the file descriptor for the file, then the file will be marked allocated on disk but no directory entry will point to it.

它已成功打开了该文件。但是，如果在最后一个进程关闭该文件的文件描述符之前发生了崩溃，那么该文件在磁盘上将被标记为已分配，但没有任何目录项指向它。

File systems handle this case in one of two ways. The simple solution is that on recovery, after reboot, the file system scans the whole file system for files that are marked allocated, but have no directory entry pointing to them. If any such file exists, then it can free those files.

文件系统以两种方式之一处理这种情况。简单的解决方案是在重启后的恢复过程中，文件系统扫描整个文件系统，查找那些被标记为已分配但没有目录项指向它们的文件。如果存在任何此类文件，则可以释放这些文件。

The second solution doesn’t require scanning the file system. In this solution, the file system records on disk (e.g., in the super block) the inode inumber of a file whose link count drops to zero but whose reference count isn’t zero. If the file system removes the file when its reference count reaches 0 , then it updates the on-disk list by removing that inode from the list. On recovery, the file system frees any file in the list.

第二种方案不需要扫描文件系统。在这种方案中，文件系统在磁盘上（例如在超级块中）记录那些链接数降为零但引用数不为零的文件的 inode 编号。如果文件系统在文件的引用数达到 0 时将其删除，那么它会通过从列表中移除该 inode 来更新磁盘上的列表。在恢复（Recovery）时，文件系统会释放列表中记录的所有文件。

Xv6 implements neither solution, which means that inodes may be marked allocated on disk, even though they are not in use anymore. This means that over time xv6 runs the risk that it may run out of disk space.

Xv6 没有实现这两种方案，这意味着某些 inode 可能会在磁盘上被标记为已分配，即使它们已不再使用。这意味着随着时间的推移，xv6 面临着耗尽磁盘空间的风险。

## 10.10 Code: Inode content

The on-disk inode structure, struct dinode, contains a size and an array of block numbers (see Figure 10.3. The inode data is found in the blocks listed in the dinode 's addrs array. The first

磁盘上的 inode 结构体 `struct dinode` 包含一个大小字段和一个块号数组（见图 10.3）。Inode 的数据存储在 `dinode` 的 `addrs` 数组所列出的块中。前

NDIRECT blocks of data are listed in the first NDIRECT entries in the array; these blocks are called direct blocks. The next NINDIRECT blocks of data are listed not in the inode but in a data block called the indirect block. The last entry in the addrs array gives the address of the indirect block. Thus the first 12 kB (NDIRECT x BSIZE) bytes of a file can be loaded from blocks listed in the inode, while the next 256 kB (NINDIRECT x BSIZE) bytes can only be loaded after consulting the indirect block. This is a good on-disk representation but a complex one for clients. The function bmap manages the representation so that higher-level routines, such as readi and writei, which we will see shortly, do not need to manage this complexity. bmap returns the disk block number of the bn’th data block for the inode ip. If ip does not have such a block yet, bmap allocates one.

NDIRECT 个数据块列在数组的前 NDIRECT 个条目中；这些块被称为直接块。接下来的 NINDIRECT 个数据块不直接列在 inode 中，而是列在一个被称为间接块的数据块中。`addrs` 数组的最后一个条目给出了间接块的地址。因此，文件的前 12 kB（NDIRECT x BSIZE）字节可以从 inode 中列出的块中加载，而接下来的 256 kB（NINDIRECT x BSIZE）字节只能在查询间接块后才能加载。这是一种很好的磁盘表示形式，但对客户端来说比较复杂。函数 `bmap` 管理这种表示形式，以便更高级别的例程（如我们稍后将看到的 `readi` 和 `writei`）不需要处理这种复杂性。`bmap` 返回 inode `ip` 的第 `bn` 个数据块的磁盘块号。如果 `ip` 还没有这样一个块，`bmap` 会分配一个。

The function bmap (5283) begins by picking off the easy case: the first NDIRECT blocks are listed in the inode itself (5288-5296), The next NINDIRECT blocks are listed in the indirect block at ip->addrs [NDIRECT]. bmap reads the indirect block (5308) and then reads a block number from the right position within the block (5309). If the block number exceeds NDIRECT+NINDIRECT, bmap panics; writei contains the check that prevents this from happening (5415). bmap allocates blocks as needed. An ip->addrs [] or indirect entry of zero indicates that no block is allocated. As bmap encounters zeros, it replaces them with the numbers of fresh blocks, allocated on demand (5289-5290) (5302-5303). itrunc frees a file’s blocks, resetting the inode’s size to zero. itrunc (5327) starts by freeing the direct blocks (5333-5338), then the ones listed in the indirect block (5343-5346), and finally the indirect block itself (5348-5349). bmap makes it easy for readi and writei to get at an inode’s data. readi (5373) starts by making sure that the offset and count are not beyond the end of the file. Reads that start beyond the end of the file return an error (5378-5379) while reads that start at or cross the end of the file return fewer bytes than requested (5380-5381). The main loop processes each block of the file, copying data from the buffer into dst (5383-5395), writei (5408) is identical to readi, with three exceptions: writes that start at or cross the end of the file grow the file, up to the maximum file size (5415-5416), the loop copies data into the buffers instead of out (5424); and if the write has extended the file, writei must update its size (5432-5433).

函数 `bmap` (5283) 首先处理简单的情况：前 `NDIRECT` 个数据块直接列在 inode 自身中 (5288-5296)。接下来的 `NINDIRECT` 个数据块则列在位于 `ip->addrs[NDIRECT]` 的一级间接块中。`bmap` 读取该间接块 (5308)，然后从该块中的正确位置读取块号 (5309)。如果块号超过了 `NDIRECT+NINDIRECT`，`bmap` 会触发 panic；`writei` 中包含的检查机制会防止这种情况发生 (5415)。`bmap` 根据需要分配数据块。`ip->addrs[]` 或间接块条目为零表示未分配数据块。当 `bmap` 遇到零时，它会将其替换为按需分配的新块号 (5289-5290) (5302-5303)。`itrunc` 释放文件的所有数据块，并将 inode 的大小重置为零。`itrunc` (5327) 首先释放直接块 (5333-5338)，然后释放间接块中列出的块 (5343-5346)，最后释放间接块本身 (5348-5349)。`bmap` 使得 `readi` 和 `writei` 能够轻松访问 inode 的数据。`readi` (5373) 首先确保偏移量和读取数量没有超出文件末尾。从文件末尾之后开始的读取将返回错误 (5378-5379)，而从文件末尾之前开始但跨越末尾的读取所返回的字节数将少于请求的数量 (5380-5381)。主循环处理文件的每个数据块，将数据从缓冲区复制到 `dst` (5383-5395)。`writei` (5408) 与 `readi` 基本相同，但有三个例外：从文件末尾开始或跨越末尾的写入会增加文件大小，直至达到最大文件限制 (5415-5416)；循环将数据复制进缓冲区而不是拷出 (5424)；如果写入扩展了文件，`writei` 必须更新文件的大小 (5432-5433)。

The function stati (5359) copies inode metadata into the stat structure, which is exposed to user programs via the stat system call.

函数 `stati` (5359) 将 inode 的元数据复制到 `stat` 结构体中，该结构体通过 `stat` 系统调用暴露给用户程序。

## 10.11 Code: directory layer

A directory is implemented internally much like a file. Its inode has type and its data is a sequence of directory entries. Each entry is a struct dirent (4165), which contains a name and an inode number. The name is at most DIRSIZ (14) characters; if shorter, it is terminated by a NULL (0) byte. Directory entries with inode number zero are free.

目录在内部实现上与文件非常相似。它的 inode 类型为 ，其数据是一系列目录项。每个目录项都是一个 struct dirent (4165)，包含一个名称和一个 inode 编号。名称最多为 DIRSIZ (14) 个字符；如果较短，则以 NULL (0) 字节结束。inode 编号为零的目录项表示该项为空闲。

The function dirlookup (5453) searches a directory for an entry with the given name. If it finds one, it returns a pointer to the corresponding inode, unlocked, and sets to the byte offset of the entry within the directory, in case the caller wishes to edit it. If dirlookup finds an entry with the right name, it updates *poff and returns an unlocked inode obtained via iget. dirlookup is the reason that iget returns unlocked inodes. The caller has locked dp, so if the lookup was for ., an alias for the current directory, attempting to lock the inode before returning would try to re-lock dp and deadlock. (There are more complicated deadlock scenarios involving multiple processes and . . , an alias for the parent directory; . is not the only problem.) The caller can unlock dp and then lock ip, ensuring that it only holds one lock at a time.

函数 dirlookup (5453) 在目录中搜索具有给定名称的条目。如果找到，它将返回指向相应 inode 的指针（未锁定），并将 设置为该条目在目录内的字节偏移量，以备调用者希望对其进行编辑。如果 dirlookup 找到了名称正确的条目，它会更新 *poff 并返回通过 iget 获取的未锁定 inode。dirlookup 是 iget 返回未锁定 inode 的原因。调用者已经锁定了 dp，因此如果查找的是 .（当前目录的别名），在返回前尝试锁定该 inode 将会导致尝试重新锁定 dp 从而引发死锁。（还存在涉及多个进程和 ..（父目录别名）的更复杂的死锁场景；. 并不是唯一的问题。）调用者可以先解锁 dp 然后再锁定 ip，从而确保一次只持有一个锁。

The function dirlink (5481) writes a new directory entry with the given name and inode number into the directory dp. If the name already exists, dirlink returns an error (5487-5491). The main loop reads directory entries looking for an unallocated entry. When it finds one, it stops the loop early (5493-5498), with off set to the offset of the available entry. Otherwise, the loop ends with off set to dp->size. Either way, dirlink then adds a new entry to the directory by writing at offset off (5502-5503).

函数 dirlink (5481) 将具有给定名称和 inode 编号的新目录项写入目录 dp。如果该名称已存在，dirlink 将返回错误 (5487-5491)。主循环读取目录项以寻找未分配的条目。当找到一个时，它会提前停止循环 (5493-5498)，并将 off 设置为可用条目的偏移量。否则，循环结束时 off 被设置为 dp->size。无论哪种情况，dirlink 随后都会通过在偏移量 off 处写入来向目录添加新条目 (5502-5503)。

## 10.12 Code: Path names

Path name lookup involves a succession of calls to dirlookup, one for each path component. namei (5590) evaluates path and returns the corresponding inode. The function nameiparent is a variant: it stops before the last element, returning the inode of the parent directory and copying the final element into name. Both call the generalized function namex to do the real work. namex (5555) starts by deciding where the path evaluation begins. If the path begins with a slash, evaluation begins at the root; otherwise, the current directory (5559-5562). Then it uses skipelem to consider each element of the path in turn (5564). Each iteration of the loop must look up name in the current inode ip. The iteration begins by locking ip and checking that it is a directory. If not, the lookup fails (5565-5569). (Locking ip is necessary not because ip->type can change underfoot-it can’t-but because until ilock runs, ip->type is not guaranteed to have been loaded from disk.) If the call is nameiparent and this is the last path element, the loop stops early, as per the definition of nameiparent; the final path element has already been copied into name, so namex need only return the unlocked ip (5570-5574). Finally, the loop looks for the path element using dirlookup and prepares for the next iteration by setting ip next (5575-5580). When the loop runs out of path elements, it returns ip.

路径名查找涉及对 `dirlookup` 的一系列调用，路径中的每个分量对应一次调用。`namei` (5590) 解析路径并返回相应的 inode。函数 `nameiparent` 是一个变体：它在最后一个元素之前停止，返回父目录的 inode，并将最后一个元素拷贝到 `name` 中。两者都调用通用函数 `namex` 来执行实际工作。namex (5555) 首先决定路径求值的起点。如果路径以斜杠开头，则从根目录开始求值；否则，从当前目录开始 (5559-5562)。接着，它使用 skipelem 依次处理路径中的每个元素 (5564)。循环的每次迭代都必须在当前 inode ip 中查找 name。迭代开始时先锁定 ip 并检查其是否为目录。如果不是，则查找失败 (5565-5569)。（锁定 ip 是必要的，这并非因为 ip->type 会意外改变——它不会——而是因为在 ilock 运行之前，无法保证 ip->type 已从磁盘加载。）如果调用是 nameiparent 且当前是最后一个路径元素，循环会按照 nameiparent 的定义提前停止；最后一个路径元素已经拷贝到 name 中，因此 namex 只需返回解锁后的 ip (5570-5574)。最后，循环使用 dirlookup 寻找路径元素，并通过设置 ip = next 为下一次迭代做准备 (5575-5580)。当循环处理完所有路径元素时，它返回 ip。

The procedure namex may take a long time to complete: it could involve several disk operations to read inodes and directory blocks for the directories traversed in the pathname (if they are not in the buffer cache). Xv6 is carefully designed so that if an invocation of namex by one kernel thread is blocked on a disk I/O, another kernel thread looking up a different pathname can proceed concurrently. namex locks each directory in the path separately so that lookups in different directories can proceed in parallel.

namex 过程可能需要很长时间才能完成：它可能涉及多次磁盘操作，以读取路径名中遍历到的目录的 inode 和目录块（如果它们不在缓冲区缓存中）。xv6 经过精心设计，如果一个内核线程调用的 namex 因磁盘 I/O 而阻塞，另一个查找不同路径名的内核线程可以并发执行。namex 分别锁定路径中的每个目录，以便在不同目录中的查找可以并行进行。

This concurrency introduces some challenges. For example, while one kernel thread is looking up a pathname another kernel thread may be changing the directory tree by unlinking a directory. A potential risk is that a lookup may be searching a directory that has been deleted by another kernel thread and its blocks have been re-used for another directory or file.

这种并发性带来了一些挑战。例如，当一个内核线程正在查找路径名时，另一个内核线程可能正在通过 unlink 删除目录来更改目录树。一个潜在的风险是，查找操作可能正在搜索一个已被另一个内核线程删除的目录，且该目录的块已被重新用于另一个目录或文件。

Xv6 avoids such races. For example, when executing dirlookup in namex, the lookup thread holds the lock on the directory and dirlookup returns an inode that was obtained using iget. iget increases the reference count of the inode. Only after receiving the inode from dirlookup does namex release the lock on the directory. Now another thread may unlink the inode from the directory but xv6 will not delete the inode yet, because the reference count of the inode is still larger than zero.

Xv6 避免了此类竞争。例如，在 `namex` 中执行 `dirlookup` 时，查找线程持有该目录的锁，并且 `dirlookup` 返回一个通过 `iget` 获取的索引节点。`iget` 会增加该索引节点的引用计数。只有在从 `dirlookup` 接收到索引节点后，`namex` 才会释放该目录的锁。此时，另一个线程可能会将该索引节点从其所在的目录中取消链接。xv6 避免了这种情况。例如，在 dirlookup 中查找条目时，如果找到了匹配的条目，dirlookup 会通过 iget 获取相关的 inode。iget 会增加 inode 的引用计数。只有当引用计数降至零时，xv6 才会释放 inode。通过在持有目录锁的同时调用 iget，namex 确保了在查找过程中该 inode 不会被释放。如果另一个线程删除了该目录，虽然链接数可能变为零，但 xv6 暂时还不会删除该 inode，因为该 inode 的引用计数仍然大于零。

Another risk is deadlock. For example, next points to the same inode as ip when looking up “.”. Locking next before releasing the lock on ip would result in a deadlock. To avoid this deadlock, namex unlocks the directory before obtaining a lock on next. Here again we see why the separation between iget and ilock is important.

另一个风险是死锁。例如，在查找“.”时，`next` 指向的 inode 与 `ip` 相同。如果在释放 `ip` 的锁之前锁定 `next`，就会导致死锁。为了避免这种死锁，`namex` 在获取 `next` 的锁之前先解锁目录。这里我们再次看到了 `iget` 和 `ilock` 分离的重要性。

## 10.13 File descriptor layer

A cool aspect of the Unix interface is that most resources in Unix are represented as files, including devices such as the console, pipes, and of course, real files. The file descriptor layer is the layer that achieves this uniformity.

Unix 接口的一个酷炫之处在于，Unix 中的大多数资源都表示为文件，包括控制台等设备、管道，当然还有真正的文件。文件描述符层就是实现这种统一性的层。

Xv6 gives each process its own table of open files, or file descriptors, as we saw in Chapter 1. Each open file is represented by a struct file (4200), which is a wrapper around either an inode or a pipe, plus an I/O offset. Each call to open creates a new open file (a new struct file): if multiple processes open the same file independently, the different instances will have different I/O offsets. On the other hand, a single open file (the same struct file) can appear multiple times in one process’s file table and also in the file tables of multiple processes. This would happen if one process used open to open the file and then created aliases using dup or shared it with a child using fork. A reference count tracks the number of references to a particular open file. A file can be open for reading or writing or both. The readable and writable fields track this.

正如我们在第 1 章中看到的，Xv6 为每个进程提供了各自的打开文件表（即文件描述符表）。每个打开的文件都由一个 `struct file` (4200) 表示，它是对 inode 或管道的封装，外加一个 I/O 偏移量。每次调用 `open` 都会创建一个新的打开文件（一个新的 `struct file`）：如果多个进程独立打开同一个文件，不同的实例将拥有不同的 I/O 偏移量。另一方面，同一个打开文件（同一个 `struct file`）可以多次出现在一个进程的文件表中，也可以出现在多个进程的文件表中。如果一个进程使用 `open` 打开文件，然后使用 `dup` 创建别名，或者使用 `fork` 与子进程共享，就会发生这种情况。引用计数跟踪指向特定打开文件的引用数量。文件可以为了读取、写入或两者兼而有之而打开，`readable` 和 `writable` 字段记录了这些状态。

All the open files in the system are kept in a global file table, the ftable. The file table has functions to allocate a file (filealloc), create a duplicate reference (filedup), release a reference (fileclose), and read and write data (fileread and filewrite).

系统中所有打开的文件都保存在一个全局文件表 `ftable` 中。该文件表具有分配文件 (`filealloc`)、创建重复引用 (`filedup`)、释放引用 (`fileclose`) 以及读写数据 (`fileread` 和 `filewrite`) 的函数。

The first three follow the now-familiar form. filealloc (5679) scans the file table for an unreferenced file ( ref ) and returns a new reference; filedup (5702) increments the reference count; and fileclose (5714) decrements it. When a file’s reference count reaches zero, fileclose releases the underlying pipe or inode, according to the type.

前三个函数遵循我们现在已经熟悉的模式。`filealloc` (5679) 在文件表中扫描未被引用的文件（`ref` 为 0）并返回一个新的引用；`filedup` (5702) 增加引用计数；而 `fileclose` (5714) 则减少引用计数。当一个文件的引用计数达到零时，`fileclose` 会根据文件类型释放底层的管道或 inode。

The functions filestat, fileread, and filewrite implement the stat, read, and write operations on files. filestat (5753) is only allowed on inodes and calls stati. fileread and filewrite check that the operation is allowed by the open mode and then pass the call through to either the pipe or inode implementation. If the file represents an inode, fileread and filewrite use the I/O offset as the offset for the operation and then advance it (5787-5788)(5830-5831). Pipes have no concept of offset. Recall that the inode functions require the caller to handle locking (57595761 (5786-5789) (5829-5832). The inode locking has the convenient side effect that the read and write offsets are updated atomically, so that multiple writing to the same file simultaneously cannot overwrite each other’s data, though their writes may end up interlaced.

函数 `filestat`、`fileread` 和 `filewrite` 实现了对文件的 `stat`、`read` 和 `write` 操作。`filestat` (5753) 仅允许在 inode 上调用，并会调用 `stati`。`fileread` 和 `filewrite` 会检查操作是否被打开模式（open mode）所允许，然后将调用传递给管道或 inode 的实现。如果文件代表一个 inode，`fileread` 和 `filewrite` 会将 I/O 偏移量作为操作的偏移量，并随后将其递增 (5787-5788)(5830-5831)。管道没有偏移量的概念。回想一下，inode 函数要求调用者处理锁 (5759-5761) (5786-5789) (5829-5832)。inode 锁有一个便利的副作用，即读写偏移量的更新是原子性的，因此多个进程同时向同一个文件写入时不会覆盖彼此的数据，尽管它们的写入内容最终可能会交织在一起。

## 10.14 Code: System calls

With the functions that the lower layers provide, the implementation of most system calls is trivial (see (5850)). There are a few calls that deserve a closer look.

有了底层提供的这些函数，大多数系统调用的实现都非常简单（见 (5850)）。有几个调用值得进一步观察。

The functions sys_link and sys_unlink edit directories, creating or removing references to inodes. They are another good example of the power of using transactions. sys_link (6002) begins by fetching its arguments, two strings old and new (6007). Assuming old exists and is not a directory (6011-6014), sys_link increments its ip->nlink count. Then sys_link calls nameiparent to find the parent directory and final path element of new (6027) and creates a new directory entry pointing at old 's inode (6030). The new parent directory must exist and be on the same device as the existing inode: inode numbers only have a unique meaning on a single disk. If an error like this occurs, sys_link must go back and decrement ip->nlink.

函数 `sys_link` 和 `sys_unlink` 用于编辑目录，创建或删除对 inode 的引用。它们是使用事务威力的另一个绝佳范例。`sys_link` (6002) 首先获取其参数，即两个字符串 `old` 和 `new` (6007)。假设 `old` 存在且不是目录 (6011-6014)，`sys_link` 会增加其 `ip->nlink` 计数。接着，`sys_link` 调用 `nameiparent` 来寻找 `new` 的父目录和路径的最后一个元素 (6027)，并创建一个指向 `old` 的 inode 的新目录项 (6030)。新的父目录必须存在，并且与现有的 inode 位于同一设备上：inode 编号仅在单个磁盘上具有唯一含义。如果发生此类错误，`sys_link` 必须回退并递减 `ip->nlink`。

Transactions simplify the implementation because it requires updating multiple disk blocks, but we don’t have to worry about the order in which we do them. They either will all succeed or none. For example, without transactions, updating ip->nlink before creating a link, would put the file system temporarily in an unsafe state, and a crash in between could result in havoc. With transactions we don’t have to worry about this. sys_link creates a new name for an existing inode. The function create (6124) creates a new name for a new inode. It is a generalization of the three file creation system calls: open with the O_CREATE flag makes a new ordinary file, mkdir makes a new directory, and mkdev makes a new device file. Like sys_link, create starts by calling nameiparent to get the inode of the parent directory. It then calls dirlookup to check whether the name already exists (6089). If the name does exist, create’s behavior depends on which system call it is being used for: open has different semantics from mkdir and mkdev. If create is being used on behalf of open (type T_FILE) and the name that exists is itself a regular file, then open treats that as a success, so create does too (6138). Otherwise, it is an error (6139-6140). If the name does not already exist, create now allocates a new inode with ialloc (6143). If the new inode is a directory, create initializes it with . and . . entries. Finally, now that the data is initialized properly, create can link it into the parent directory (6158), create, like sys_link, holds two inode locks simultaneously: ip and dp. There is no possibility of deadlock because the inode ip is freshly allocated: no other process in the system will hold ip 's lock and then try to lock dp.

事务简化了实现，因为虽然需要更新多个磁盘块，但我们不必担心操作的顺序。它们要么全部成功，要么全部不成功。例如，如果没有事务，在创建链接之前更新 ip->nlink 会使文件系统暂时处于不安全状态，期间如果发生崩溃可能会导致严重混乱。有了事务，我们就不必担心这个问题。sys_link 为现有的 inode 创建一个新名称。函数 create (6124) 则为新的 inode 创建一个新名称。它是三种文件创建系统调用的通用实现：带有 O_CREATE 标志的 open 用于创建普通文件，mkdir 用于创建目录，mkdev 用于创建设备文件。与 sys_link 类似，create 首先调用 nameiparent 以获取父目录的 inode。接着，它调用 dirlookup 来检查该名称是否已存在 (6089)。如果名称确实存在，create 的行为取决于它服务于哪个系统调用：open 的语义与 mkdir 和 mkdev 不同。如果 create 是代表 open (类型为 T_FILE) 被调用，且存在的名称本身也是一个普通文件，那么 open 将其视为成功，create 也是如此 (6138)。否则，这将被视为错误 (6139-6140)。如果名称尚不存在，create 现在会通过 ialloc 分配一个新的 inode (6143)。如果新 inode 是一个目录，create 会用 . 和 .. 条目对其进行初始化。最后，在数据正确初始化后，create 可以将其链接到父目录中 (6158)。与 sys_link 一样，create 同时持有两个 inode 锁：ip 和 dp。这里不存在死锁的可能性，因为 inode ip 是新分配的：系统中没有其他进程会先持有 ip 的锁，然后再尝试锁定 dp。

Using create, it is easy to implement sys_open, sys_mkdir, and sys_mknod. sys_open (6185) is the most complex, because creating a new file is only a small part of what it can do. If open is passed the O_CREATE flag, it calls create (6201). Otherwise, it calls namei (6207), create returns a locked inode, but namei does not, so sys_open must lock the inode itself. This provides a convenient place to check that directories are only opened for reading, not writing. Assuming the inode was obtained one way or the other, sys_open allocates a file and a file descriptor (6225) and then fills in the file (6237-6242), Note that no other process can access the partially initialized file since it is only in the current process’s table.

利用 `create` 函数，可以轻松实现 `sys_open`、`sys_mkdir` 和 `sys_mknod`。`sys_open` (6185) 是其中最复杂的，因为创建新文件只是其功能的一小部分。如果 `open` 被传入了 `O_CREATE` 标志，它会调用 `create` (6201)。否则，它会调用 `namei` (6207)。由于 `create` 返回的是一个已加锁的 inode，而 `namei` 则不是，因此 `sys_open` 必须亲自为该 inode 加锁。这提供了一个方便的位置来检查目录是否仅以只读方式打开，而非写入。假设已经通过某种方式获取了 inode，`sys_open` 会分配一个文件结构体和一个文件描述符 (6225)，然后填充该文件结构体 (6237-6242)。请注意，没有其他进程可以访问这个尚未初始化完成的文件，因为它仅存在于当前进程的表中。

Chapter 9 examined the implementation of pipes before we even had a file system. The function sys_pipe connects that implementation to the file system by providing a way to create a pipe pair. Its argument is a pointer to space for two integers, where it will record the two new file descriptors. Then it allocates the pipe and installs the file descriptors.

第 9 章在介绍文件系统之前就已经探讨了管道的实现。`sys_pipe` 函数通过提供一种创建管道对的方法，将该实现与文件系统连接起来。它的参数是一个指向两个整数空间的指针，用于记录两个新的文件描述符。随后，它分配管道并安装这两个文件描述符。

## 10.15 Real world

The buffer cache in a real-world operating system is significantly more complex than xv6’s, but it serves the same two purposes: caching and synchronizing access to the disk. Xv6’s buffer cache, like V6’s, uses a simple least recently used (LRU) eviction policy; there are many more complex policies that can be implemented, each good for some workloads and not as good for others. A more efficient LRU cache would eliminate the linked list, instead using a hash table for lookups and a heap for LRU evictions. Modern buffer caches are typically integrated with the virtual memory system to support memory-mapped files.

现实世界操作系统中的缓冲池（buffer cache）比 xv6 的要复杂得多，但其目的相同：缓存以及同步对磁盘的访问。xv6 的缓冲池与 V6 一样，使用简单的最近最少使用（LRU）置换策略；实际上可以实现许多更复杂的策略，每种策略都适用于某些特定的工作负载，而在其他负载下表现不佳。一个更高效的 LRU 缓存会取消链表结构，转而使用哈希表进行查找，并使用堆来进行 LRU 置换。现代缓冲池通常与虚拟内存系统集成，以支持内存映射文件（mmap）。

Xv6’s logging system is inefficient. A commit cannot occur concurrently with file-system system calls. The system logs entire blocks, even if only a few bytes in a block are changed. It performs synchronous log writes, a block at a time, each of which is likely to require an entire disk rotation time. Real logging systems address all of these problems.

xv6 的日志系统效率较低。提交（commit）操作无法与文件系统的系统调用并发执行。即使一个块中只更改了几个字节，系统也会记录整个数据块。它以每次一个块的方式执行同步日志写入，每一次写入都可能需要消耗整个磁盘旋转周期的时间。现实中的日志系统解决了所有这些问题。

Logging is not the only way to provide crash recovery. Early file systems used a scavenger during reboot (for example, the UNIX fsck program) to examine every file and directory and the block and inode free lists, looking for and resolving inconsistencies. Scavenging can take hours for large file systems, and there are situations where it is not possible to resolve inconsistencies in a way that causes the original system calls to be atomic. Recovery from a log is much faster and causes system calls to be atomic in the face of crashes.

日志并非提供崩溃恢复的唯一方法。早期的文件系统在重启期间使用扫描程序（例如 UNIX 的 fsck 程序）来检查每个文件、目录以及块和 inode 的空闲列表，寻找并解决不一致问题。对于大型文件系统，扫描可能需要数小时，而且在某些情况下，无法以使原始系统调用保持原子性的方式来解决不一致。从日志中恢复要快得多，并且能确保系统调用在面对崩溃时具有原子性。

Xv6 uses the same basic on-disk layout of inodes and directories as early UNIX; this scheme has been remarkably persistent over the years. BSD’s UFS/FFS and Linux’s ext2/ext3 use essentially the same data structures. The most inefficient part of the file system layout is the directory, which requires a linear scan over all the disk blocks during each lookup. This is reasonable when directories are only a few disk blocks, but is expensive for directories holding many files. Microsoft Windows’s NTFS, macOS’s HFS, and Solaris’s ZFS, just to name a few, implement a directory as an on-disk balanced tree of blocks. This is complicated but guarantees logarithmic-time directory lookups.

Xv6 使用了与早期 UNIX 相同的 inode 和目录的基本磁盘布局；这种方案多年来一直保持着惊人的生命力。BSD 的 UFS/FFS 和 Linux 的 ext2/ext3 基本上使用相同的数据结构。文件系统布局中最效率低下的部分是目录，它在每次查找期间都需要对所有磁盘块进行线性扫描。当目录仅占用几个磁盘块时，这是合理的，但对于包含许多文件的目录来说，代价非常高。微软 Windows 的 NTFS、macOS 的 HFS 和 Solaris 的 ZFS（仅举几例）将目录实现为磁盘上的平衡树块。这虽然复杂，但能保证对数级时间的目录查找。

Xv6 is naive about disk failures: if a disk operation fails, xv6 panics. Whether this is reasonable depends on the hardware: if an operating systems sits atop special hardware that uses redundancy to mask disk failures, perhaps the operating system sees failures so infrequently that panicking is okay. On the other hand, operating systems using plain disks should expect failures and handle them more gracefully, so that the loss of a block in one file doesn’t affect the use of the rest of the file system.

Xv6 对磁盘故障的处理非常简单：如果磁盘操作失败，xv6 就会 panic。这是否合理取决于硬件：如果操作系统运行在利用冗余来屏蔽磁盘故障的特殊硬件之上，那么操作系统看到故障的频率可能非常低，以至于 panic 也是可以接受的。另一方面，使用普通磁盘的操作系统应该预料到故障并更优雅地处理它们，这样某个文件中一个块的损坏就不会影响文件系统其余部分的使用。

Xv6 requires that the file system fit on one disk device and not change in size. As large databases and multimedia files drive storage requirements ever higher, operating systems are developing ways to eliminate the “one disk per file system” bottleneck. The basic approach is to combine many disks into a single logical disk. Hardware solutions such as RAID are still the most popular, but the current trend is moving toward implementing as much of this logic in software as possible. These software implementations typically allow rich functionality like growing or shrinking the logical device by adding or removing disks on the fly. Of course, a storage layer that can grow or shrink on the fly requires a file system that can do the same: the fixed-size array of inode blocks used by xv6 would not work well in such environments. Separating disk management from the file system may be the cleanest design, but the complex interface between the two has led some systems, like Sun’s ZFS, to combine them. Xv6’s file system lacks many other features of modern file systems; for example, it lacks support for snapshots and incremental backup.

Xv6 要求文件系统必须安装在单个磁盘设备上，且大小不可更改。随着大型数据库和多媒体文件对存储需求的不断提高，操作系统正在开发各种方法来消除“每个文件系统一个磁盘”的瓶颈。基本方法是将多个磁盘组合成一个逻辑磁盘。虽然像 RAID 这样的硬件解决方案仍然最受欢迎，但目前的趋势是尽可能在软件中实现这些逻辑。这些软件实现通常提供丰富的功能，例如通过动态添加或移除磁盘来扩大或缩小逻辑设备。当然，一个可以动态扩缩的存储层需要一个同样具备此能力的文件系统：xv6 所使用的固定大小的 inode 块数组在这样的环境下无法良好运行。将磁盘管理与文件系统分离可能是最简洁的设计，但两者之间复杂的接口导致了一些一些系统（如 Sun 的 ZFS）将它们结合了起来。Xv6 的文件系统还缺少现代文件系统的许多其他特性；例如，它缺乏对快照和增量备份的支持。

Modern Unix systems allow many kinds of resources to be accessed with the same system calls as on-disk storage: named pipes, network connections, remotely-accessed network file systems, and monitoring and control interfaces such as /proc. Instead of xv6’s if statements in fileread and filewrite, these systems typically give each open file a table of function pointers, one per operation, and call the function pointer to invoke that inode’s implementation of the call. Network file systems and user-level file systems provide functions that turn those calls into network RPCs and wait for the response before returning.

现代 Unix 系统允许使用与磁盘存储相同的系统调用来访问多种资源：命名管道、网络连接、远程访问的网络文件系统，以及如 /proc 等监控和控制接口。这些系统通常不会像 xv6 那样在 fileread 和 filewrite 中使用 if 语句，而是为每个打开的文件提供一个函数指针表（每个操作对应一个指针），通过调用函数指针来执行该 inode 对调用的具体实现。网络文件系统和用户级文件系统提供的函数会将这些调用转换为网络 RPC，并在返回前等待响应。

## 10.16 Exercises

1. Why panic in balloc? Can xv6 recover?
   为什么 balloc 中要使用 panic？xv6 能够从中恢复吗？
2. Why panic in ialloc? Can xv6 recover?
   为什么 ialloc 中要使用 panic？xv6 能够从中恢复吗？
3. Why doesn’t filealloc panic when it runs out of files? Why is this more common and therefore worth handling?
   为什么 filealloc 在文件资源耗尽时不会触发 panic？为什么这种情况更常见，因而值得进行处理？
4. Suppose the file corresponding to ip gets unlinked by another process between sys_link 's calls to iunlock (ip) and dirlink. Will the link be created correctly? Why or why not?
   假设在 `sys_link` 调用 `iunlock(ip)` 和 `dirlink` 之间，另一个进程取消了 `ip` 对应文件的链接（unlink）。该链接还会被正确创建吗？为什么？
5. create makes four function calls (one to ialloc and three to dirlink) that it requires to succeed. If any doesn’t, create calls panic. Why is this acceptable? Why can’t any of those four calls fail?
   `create` 进行了四次函数调用（一次 `ialloc` 和三次 `dirlink`），并要求这些调用必须成功。如果其中任何一个失败，`create` 就会调用 `panic`。为什么这样做是可接受的？为什么这四个调用中的任何一个都不应该失败？
6. sys_chdir calls iunlock(ip) before iput(cp->cwd), which might try to lock cp->cwd, yet postponing iunlock (ip) until after the iput would not cause deadlocks. Why not?
   `sys_chdir` 在调用 `iput(cp->cwd)` 之前先调用了 `iunlock(ip)`，而 `iput` 可能会尝试锁定 `cp->cwd`。然而，即使将 `iunlock(ip)` 推迟到 `iput` 之后执行也不会导致死锁。为什么？
7. Implement the lseek system call. Supporting lseek will also require that you modify filewrite to fill holes in the file with zero if lseek sets off beyond f->ip->size.
   实现 `lseek` 系统调用。支持 `lseek` 还要求你修改 `filewrite`：如果 `lseek` 将偏移量设置在 `f->ip->size` 之外，则需要用零填充文件中的空洞。
8. Add ○_TRUNC and ○_APPEND to open, so that and operators work in the shell.
   为 `open` 添加 `O_TRUNC` 和 `O_APPEND` 支持，以便 shell 中的 ` ` 和 ` ` 操作符能够正常工作。
9. Modify the file system to support symbolic links.
   修改文件系统以支持符号链接。
10. Modify the file system to support named pipes.
   修改文件系统以支持命名管道。
11. Modify the file and VM system to support memory-mapped files.
   修改文件系统和虚拟内存（VM）系统以支持内存映射文件。

