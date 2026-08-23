# Writing style

These rules govern prose in this repository: documentation, commit messages,
issue text. They do not govern code or code comments.

Vale enforces the mechanical parts. Run `vale docs/ *.md` before committing, or
install the git hooks with `tools/hooks/install.sh` and it runs for you. The
rules live in `styles/Klaus/`. Anything Vale cannot check is below, and the
short version is in `CLAUDE.md`.

## Reader

Write for a fluent non-native English speaker. Do not simplify vocabulary,
shorten sentences, or explain standard technical terms. The constructions that
cost a second-language reader time are not the ones that cost a beginner time,
and these are the ones to target.

Prefer a single Latinate verb to a phrasal verb. Write `investigate` rather
than `look into`, `postpone` rather than `put off`, `start` rather than
`spin up`, `deploy` rather than `roll out`. A phrasal verb is opaque, because
its meaning does not follow from the verb and the particle. International
technical vocabulary is transparent by comparison.

Use no idioms, and no metaphors drawn from sport, US politics, or military
history. `Ballpark figure`, `home stretch`, `move the goalposts` and
`boil the ocean` are all banned. Say the thing directly.

Keep noun stacks to three words. Rewrite `authentication token refresh failure
handler` as `the handler for failures when refreshing an authentication token`.
A native reader parses a long stack by recognition. Every other reader parses
it by trial and error.

Keep the function words that native writers drop. Write `the config that the
loader parses`, not `the config the loader parses`. Keep `that` after verbs of
saying and thinking: `note that the pool saturates`. Keep articles everywhere.

Some English words differ from their cognates in other European languages.
`Control` means to direct, not to check, so write `verify`. `Actual` means
real, not current, so write `current`. `Eventually` means in the end, not
possibly, so write `in the end`.

Use no double negatives and no `not un-` constructions. State the positive.

One subordinate clause per sentence is the working limit. Split any sentence
that makes the reader hold two clauses open before the resolution arrives.

## Form

State the conclusion first, then the reasoning that supports it, and include
the causal chain. Not `use a bounded queue here` but `the producer outruns the
consumer during replay, so an unbounded queue grows until the heap is
exhausted, and a bounded queue prevents that`.

Readability is not compression. Dense technical shorthand takes longer to read
than the same content in ordinary sentences, because the reader must decompress
it. Prefer the version that reads faster, even when it is longer. Where this
conflicts with a sentence-length target, readability wins, and the length
targets are diagnostics rather than limits.

Write connected paragraphs. Use a list only when the items are truly parallel
and unordered: options, parameters, enumerated failure cases. Four
bullets that are each a full sentence are a paragraph that has been broken
apart, so write the paragraph.

Make the actor of the sentence its grammatical subject, and make what that
actor does the main verb. Write `the parser validates the schema`, not
`validation of the schema is performed by the parser`. Do not turn verbs into
nouns: `we decided`, not `we made a decision`.

Start each sentence with information the reader already has, and put the new
information at the end. That ordering is what makes a paragraph flow rather
than read as assertions in arbitrary order. Put the point you want emphasised
at the end of the sentence, not in a subordinate clause in the middle.

Aim for 15 to 25 words per sentence, and vary the length. A short sentence
after two long ones carries weight. Five short ones in a row read like a
telegram. Paragraphs run three to six sentences.

Give concrete numbers instead of `significantly` or `several`. If you do not
have the number, name the measurement that would produce it. When you do not
know something, write `I don't know` or `I'd have to check X`, rather than a
fog of `generally` and `it depends` that leaves the reader unsure whether the
question was answered.

Use bold only for a term of art on first definition, or for a real warning. Do
not bold a phrase to mark it as important; make it important by where you put
it in the sentence. Use at most one em dash per paragraph.

## Procedures, commands and algorithms

Where these rules conflict with the rules above, this section wins.

Write procedures as numbered steps, one action per step. This is the case where
a list is correct, because the items are ordered and the order is the content.
Start each step with an imperative verb and keep it under 20 words. If a step
needs three sentences of justification, put the justification in a paragraph
after the step.

Suspend the sentence-rhythm rules inside a procedure. Prose benefits from
varied sentence length. A procedure benefits from uniform parallel structure,
because the reader scans it rather than reading it.

Use one term for one thing throughout. Do not alternate between `directory` and
`folder`, or between `delete`, `remove` and `purge`. Use the term the tool's own
documentation uses and keep it for the whole document.

State the goal and the end state before the first step, then the prerequisites,
then the steps. Conclusion-first still applies, and for a procedure the
conclusion is what the reader will have when they finish.

Put every command in a fenced block, exactly as it should be typed. Do not
inline a command in a sentence and leave the reader to assemble it. Do not
include the shell prompt character. Do not mix command and output in one block:
if you show output, put it in its own labelled block.

Say what a command does before the block, and what success looks like after it.
`Three containers should now be in state Up` is the most useful sentence in most
procedures, because without it the reader cannot tell whether to continue.
Where failure is likely, say what the common failure looks like and what it
means.

Mark placeholders with one convention and state it once. Never leave a value
that looks real but is not.

Put warnings before the destructive command, not after. Name the precondition
that makes it safe, and the way back if it turns out not to be.

For an algorithm, give the invariant in prose and the mechanics in code or
pseudocode. Neither alone is sufficient: prose alone makes the reader
reconstruct the loop, and code alone makes them infer why it terminates. Define
every symbol before it appears. Give complexity as a bound with the variable
named, such as `O(n log n) in the number of records`, rather than `efficient`.

## Diagrams

A diagram earns its place when it lets a reader see a mechanism that they would
otherwise assemble from prose. If a sentence says it faster, write the
sentence.

Draw the mechanism rather than its name. A row of boxes labelled with function
names repeats the prose. A picture of the board row, with the anchor marked and
the two search directions shown, tells the reader something the prose did not.

Width is the constraint that bites first. A `graph LR` chain grows rightward
without limit, so eight labelled stages render about 2,000 pixels wide and
force horizontal scrolling on a laptop. Long lines are hard to read, and that
applies to figures as much as to text.

Use `graph TD` by default, because a vertical diagram grows in the direction
the page already scrolls. Use `graph LR` only when left-to-right order carries
meaning. The word graph in `algorithms.md` is horizontal because its edges
spell words in reading order, and turning it vertical would lose that.

Keep every diagram under 800 pixels of estimated width.
`tools/check_diagrams.py` measures this and the pre-commit hook runs it. The
measurement is an estimate from label lengths rather than a real render, which
is accurate enough to separate a diagram that fits from one that does not.

Label the arrows. An unlabelled arrow means "related somehow", while `writes`
or `invalidates` is information.

Prefer a plain text figure in a fenced block when the thing being shown is
spatial. A board row with column numbers, an anchor marker and two direction
arrows is clearer as text art than as a flowchart, and it cannot render too
wide as long as the lines stay under about 76 characters.

## Example

The bad example quotes banned constructions deliberately, so Vale is switched
off for this section.

<!-- vale off -->

Bad:

> Great question! There are a few key considerations here.
>
> **Performance**: The current implementation is not just slow — it's
> fundamentally unscalable.
>
> **Correctness**: There are potential race conditions.
>
> **Maintainability**: The code is difficult to reason about.
>
> Essentially, it's worth noting that a refactor would be beneficial.

Good:

> The bottleneck is the per-request database connection. Each handler opens its
> own connection and closes it on return, so under load the pool saturates at
> about 200 concurrent requests and everything after that blocks on
> acquisition.
>
> The same pattern causes a correctness problem. Two handlers that touch the
> same row run in separate transactions with no ordering guarantee, so a
> concurrent update can be lost. I have not reproduced this, but the code path
> allows it.
>
> A connection pool injected at construction fixes both. It is a mechanical
> change across the eleven handlers in `api/`.

<!-- vale on -->
