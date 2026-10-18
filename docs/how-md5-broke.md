# How this demo works, and how MD5 was broken

MD5 is a hash function. It turns a file into a 128-bit fingerprint. The promise was that two different files would not share a fingerprint, and that you could not build a collision on purpose. Both parts of that promise failed. This page is the short version: what the buttons on the demo do, and how that break happened.

## How this demo works

Think of MD5 as a running total. It reads the file 64 bytes at a time and updates a 128-bit state. The final state is the hash.

In 2006 Marc Stevens published FastColl, a program that finds two different 128-byte blocks with this property: start from the same state, feed in either block, and the state afterwards is the same again. The blocks are not guessed. They are constructed from a known pattern of bit differences. This project computed one pair for a fixed GIF header and one pair for a short text header, then saved the blocks. Clicking the button does not search. It reuses those blocks.

Each download is then:

- the same header
- one of the two blocks (they differ in a handful of bytes)
- the same ending

The state matches after the block, and the ending is identical, so the final MD5 matches. SHA-256 of the two files does not match. The page shows both, because that is the useful check.

### Two pictures

A GIF comment is a length byte followed by that many data bytes. FastColl always flips the high bit of byte 123 of the collision block, so that byte is a length in one file and a length 128 larger in the other. The other differing bytes sit inside comment data, where a viewer ignores them.

Both pictures are stored in the shared ending.

- In one file the comment ends first. The viewer reaches picture 1. That frame is given the longest delay GIF allows, about 11 minutes, so it looks like a still photo.
- In the other file the comment is 128 bytes longer, and those extra bytes swallow picture 1. The viewer shows picture 2.

So the two files are different, they open as different pictures, and they have one MD5. Neither file is the original upload unchanged. Both contain both pictures.

### Generate a pair

This mode skips the GIF switch. Both downloads start with the sentence `MD5 collision demo. Shared prefix ends here.` Then comes one collision block or the other, then whatever text you typed. The text is identical in both files. A hex editor shows the difference in those 128 bytes, and the hashes behave the same way: one MD5, two SHA-256 values.

### What this cannot do

It cannot make a file match an MD5 you already have. That is a different break, called a preimage, and MD5 still does not offer a practical one. It cannot take two photos exactly as the camera saved them and force those untouched files to collide. The downloads are built for this trick. It also cannot start from two unrelated headers. That slower method is the next section.

## How MD5 was broken

Ronald Rivest published MD5 in 1991. For a hash used as an identifier, two properties matter. A collision means two different inputs with the same hash. A preimage means an input that hits a hash you chose in advance. The birthday bound says a random search for an MD5 collision takes about 2^64 attempts. That is large, but it is not the attack that mattered. The attack that mattered constructs the collision directly.

In 2004 Xiaoyun Wang and Hongbo Yu, in work presented with Dengguo Feng and Xuejia Lai, showed that MD5's compression function has a differential path: a pattern of differences that the function cancels, leaving the same state. A collision could be built in minutes on a PC of that time, instead of being searched for at random. The same line of work broke MD4, and later SHA-1 fell in public as well (the SHAttered collision, 2017). A hash that is only "hard to guess" is not a hash you can use to name a file.

Stevens' FastColl made the identical-prefix case routine: same starting bytes, two crafted blocks, anything identical afterwards. A later variant called UniColl keeps the speed and lets the author choose a few bytes around a single-bit difference. That is why public demos can turn the bit flip into a length field in PNG, PDF, and other formats. This demo uses the GIF comment because FastColl's predictable bit is a single byte, and a GIF comment length is a single byte.

### Chosen-prefix collisions

Identical-prefix collisions need a shared header. A chosen-prefix collision starts from two different beginnings, both chosen by the attacker, and still lands on one hash. It costs hours on a normal machine, not a click. It is still cheap next to what MD5 was supposed to cost.

In 2008 a group including Alexander Sotirov, Marc Stevens, and Jacob Appelbaum used a chosen-prefix collision to build a rogue certificate authority. Browsers that still trusted MD5 for certificates would have trusted sites signed under that authority. MD5 was no longer a classroom weakness. It was a way to forge a trust anchor.

In 2012 the Flame malware used the same kind of collision against a Microsoft Terminal Server licensing certificate. The crafted file verified as if Microsoft had signed it, and that signature was used to spread the malware as a Windows update. A collision is not two random files that happened to match. It is an attacker choosing both files.

### Why this still matters

MD5 was used for years as the name of a file in malware databases and integrity checks. That only works if one hash means one file. It does not.

- Two payloads can share an MD5. A search for that hash can mix them, or a blocklist can miss the second file because the first hash was already filed.
- A file that passes an MD5 integrity check may still have been swapped, if the checker only stores MD5 and the attacker can append or rewrite data around a collision.
- MD5 remains fine for catching accidental damage, such as a bad download, when nobody is crafting the input. It is not fine for identifying a file or for a signature that is supposed to stop an attacker.

Identify files with SHA-256. If an old record still lists MD5, keep it only as a legacy alias next to a stronger hash, and do not treat a match as proof that the bytes are the same.
