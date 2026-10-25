using Terminal.Gui;

namespace Notas.Cli.Tests;

public sealed class EditorTests
{
    [Theory]
    [InlineData(Key.F2)]
    [InlineData(Key.CtrlMask | Key.S)]
    public void EditorPreservesMultilineUnicodeAndAcceptsSaveKeys(Key key)
    {
        Application.Init(new FakeDriver());
        try
        {
            using var editor = new TextView { Text = "Primera ñ\nSegunda 😊\n" };
            var stopped = false;
            var controller = new EditorController(editor, () => stopped = true);
            Assert.True(controller.Handle(new KeyEvent(key, new KeyModifiers())));
            Assert.True(stopped);
            Assert.Equal("Primera ñ\nSegunda 😊\n", controller.Result);
        }
        finally { Application.Shutdown(); }
    }

    [Theory]
    [InlineData(Key.CtrlMask | Key.C)]
    [InlineData(Key.CtrlMask | Key.Q)]
    public void CancellingEditorDoesNotReturnPartialText(Key key)
    {
        Application.Init(new FakeDriver());
        try
        {
            using var editor = new TextView { Text = "Sin guardar" };
            var stopped = false;
            var controller = new EditorController(editor, () => stopped = true);
            controller.Handle(new KeyEvent(key, new KeyModifiers()));
            Assert.True(stopped);
            Assert.Null(controller.Result);
        }
        finally { Application.Shutdown(); }
    }

    [Fact]
    public void EmojiKeyEventsAreJoinedBeforeReachingTextView()
    {
        Application.Init(new FakeDriver());
        try
        {
            using var editor = new TextView();
            var controller = new EditorController(editor, () => { });
            foreach (var character in "😊")
                Assert.True(controller.Handle(new KeyEvent((Key)character, new KeyModifiers())));
            Assert.Equal("😊", editor.Text.ToString());
        }
        finally { Application.Shutdown(); }
    }
}
