package com.github.tiagolofi.client.openai;

import java.util.List;

public record OpenAiOutput(
    String type,
    List<OpenAiContent> content
) {
    public boolean isMessage() {
        return "message".equals(type);
    }

    public OpenAiContent getFirstContent() {
        if (content == null) {
            return null;
        }
        return content.getFirst();
    }
}
