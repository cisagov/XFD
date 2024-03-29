// sendMessage.js
const amqp = require('amqplib');

async function sendMessageToQueue(message, queue) {
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();

  await channel.assertQueue(queue, { durable: true });

  // Simulate sending a message to the queue
  channel.sendToQueue(queue, Buffer.from(JSON.stringify(message)), {
    persistent: true
  });

  console.log('Message sent:', message);

  setTimeout(() => {
    connection.close();
  }, 500);
}

// Simulate sending a message
const message = {
  scriptType: 'dnstwist',
  org: 'DHS'
};
const queue = 'dnstwistQueue';
sendMessageToQueue(message, queue);
sendMessageToQueue(message, queue);
sendMessageToQueue(message, queue);
sendMessageToQueue(message, queue);
sendMessageToQueue(message, queue);
