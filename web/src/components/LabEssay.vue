<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-3">
      What's actually going on here (and how it relates to something like Claude)
    </h3>
    <div class="text-sm text-gray-600 space-y-3">
      <p>
        Every model on this page is doing the same fundamental thing: guessing an unknown value
        from patterns in known data. A naive guess assumes tomorrow looks like today. Linear
        regression draws a straight line through recent history and extends it. K Nearest
        Neighbors looks for past moments that resembled right now and averages what happened
        next. A Recurrent Neural Network (RNN), and its more capable descendant the Long
        Short-Term Memory network (LSTM), read the price history one day at a time, carrying
        forward a kind of memory of what came before, and use that memory to make a prediction.
      </p>
      <p>
        Every one of these techniques is defined by two things: the data it learns from, and the
        weights it adjusts during training to turn that data into a prediction. Change either one
        and the output changes. That's the whole idea behind the window control above: swap which
        slice of price history the model was trained on, and the forecast shifts, because you've
        changed what the model actually learned from.
      </p>
      <p>
        Large language models, like the one that helped build this page, are built on the same
        underlying idea, applied to language instead of numbers, at a scale that's hard to compare
        directly. Where this LSTM reads a sequence of stock prices and predicts the next price, an
        LLM reads a sequence of words (technically "tokens") and predicts the next one. Where this
        model trains on about a year of one stock's daily closes, an LLM trains on a huge slice of
        the internet. And where this model reads its input one step at a time, the way an RNN or
        LSTM works, most modern LLMs use a different architecture called a transformer, which
        looks at an entire sequence at once and weighs every word against every other word
        simultaneously.
      </p>
      <p>
        Different data, different scale, different architecture, but the same core idea: predict
        the next value in a sequence, given everything that came before it. That's what makes the
        sentiment control above worth trying even though it's explicitly fake: it's a small,
        honest way to feel what weighing an input more heavily actually does to a prediction, in a
        system simple enough to poke at directly.
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup></script>
